from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import Answer, Question, User, Vote
from ..ranking import hot_score
from ..schemas import AnswerOut, QuestionDetail, QuestionIn, QuestionSummary
from ..security import get_current_user, get_optional_user

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("", response_model=list[QuestionSummary])
def list_questions(
    sort: Literal["new", "active"] = "new",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    answer_count = func.count(Answer.id).label("answer_count")
    stmt = (
        select(Question, answer_count)
        .outerjoin(Answer, Answer.question_id == Question.id)
        .options(selectinload(Question.author))
        .group_by(Question.id)
    )
    if sort == "active":
        stmt = stmt.order_by(answer_count.desc(), Question.created_at.desc())
    else:
        stmt = stmt.order_by(Question.created_at.desc())

    rows = db.execute(stmt.limit(limit).offset(offset)).all()
    return [
        QuestionSummary(
            id=q.id,
            title=q.title,
            author=q.author.username,
            created_at=q.created_at,
            answer_count=count,
        )
        for q, count in rows
    ]


@router.post("", response_model=QuestionSummary, status_code=status.HTTP_201_CREATED)
def create_question(
    data: QuestionIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = Question(author_id=user.id, title=data.title.strip(), body=data.body.strip())
    db.add(q)
    db.commit()
    return QuestionSummary(
        id=q.id, title=q.title, author=user.username, created_at=q.created_at, answer_count=0
    )


@router.get("/{question_id}", response_model=QuestionDetail)
def get_question(
    question_id: int,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    q = db.get(Question, question_id, options=[selectinload(Question.author)])
    if q is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")

    rows = db.execute(
        select(Answer, func.count(Vote.id))
        .outerjoin(Vote, Vote.answer_id == Answer.id)
        .where(Answer.question_id == question_id)
        .options(selectinload(Answer.author))
        .group_by(Answer.id)
    ).all()

    my_votes: set[int] = set()
    if user is not None and rows:
        my_votes = set(
            db.scalars(
                select(Vote.answer_id).where(
                    Vote.user_id == user.id,
                    Vote.answer_id.in_([a.id for a, _ in rows]),
                )
            )
        )

    rows.sort(key=lambda r: hot_score(r[1], r[0].created_at), reverse=True)
    answers = [
        AnswerOut(
            id=a.id,
            body=a.body,
            author=a.author.username,
            created_at=a.created_at,
            votes=votes,
            voted_by_me=a.id in my_votes,
        )
        for a, votes in rows
    ]
    return QuestionDetail(
        id=q.id,
        title=q.title,
        body=q.body,
        author=q.author.username,
        created_at=q.created_at,
        answers=answers,
    )
