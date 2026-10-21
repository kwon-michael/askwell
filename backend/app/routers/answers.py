from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import DateTime, bindparam, delete, func, select, text
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Answer, ContentStatus, Question, User, Vote
from ..moderation import initial_status
from ..schemas import AnswerIn, AnswerOut, TopAnswer, VoteResult
from ..security import get_current_user

router = APIRouter(tags=["answers"])

# Written as raw SQL on purpose: it's the kind of reporting query that's easier
# to read and tune by hand than through the ORM. Only votes cast inside the
# window count, so an old answer doesn't stay on top forever.
TOP_ANSWERS_SQL = text(
    """
    SELECT a.id          AS answer_id,
           a.question_id AS question_id,
           q.title       AS question_title,
           u.username    AS author,
           COUNT(v.id)   AS votes
    FROM answers a
    JOIN questions q ON q.id = a.question_id
    JOIN users u     ON u.id = a.author_id
    JOIN votes v     ON v.answer_id = a.id AND v.created_at >= :since
    WHERE a.status = 'published' AND q.status = 'published'
    GROUP BY a.id, a.question_id, q.title, u.username
    ORDER BY votes DESC, a.id DESC
    LIMIT :limit
    """
).bindparams(bindparam("since", type_=DateTime(timezone=True)))


@router.get("/answers/top", response_model=list[TopAnswer])
def top_answers(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(TOP_ANSWERS_SQL, {"since": since, "limit": limit}).mappings()
    return [TopAnswer(**row) for row in rows]


@router.post(
    "/questions/{question_id}/answers",
    response_model=AnswerOut,
    status_code=status.HTTP_201_CREATED,
)
def create_answer(
    question_id: int,
    data: AnswerIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    question = db.get(Question, question_id)
    if question is None or question.status != ContentStatus.PUBLISHED:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")
    body = data.body.strip()
    answer = Answer(
        question_id=question_id,
        author_id=user.id,
        body=body,
        status=initial_status(body, user),
    )
    db.add(answer)
    db.commit()
    return AnswerOut(
        id=answer.id,
        body=answer.body,
        author=user.username,
        created_at=answer.created_at,
        votes=0,
        voted_by_me=False,
        status=answer.status,
    )


@router.post("/answers/{answer_id}/vote", response_model=VoteResult)
def toggle_vote(
    answer_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    answer = db.get(Answer, answer_id)
    if answer is None or answer.status != ContentStatus.PUBLISHED:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Answer not found")
    if answer.author_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can't vote on your own answer")

    existing = db.scalar(
        select(Vote).where(Vote.user_id == user.id, Vote.answer_id == answer_id)
    )
    if existing:
        db.execute(delete(Vote).where(Vote.id == existing.id))
    else:
        db.add(Vote(user_id=user.id, answer_id=answer_id))
    db.commit()

    votes = db.scalar(select(func.count(Vote.id)).where(Vote.answer_id == answer_id))
    return VoteResult(answer_id=answer_id, votes=votes, voted_by_me=existing is None)
