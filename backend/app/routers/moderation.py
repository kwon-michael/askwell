from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import Answer, ContentStatus, ModerationReview, Question, User, utcnow
from ..schemas import ReviewDecision, ReviewItem
from ..security import get_admin_user

router = APIRouter(prefix="/moderation", tags=["moderation"])

LOAD_REVIEW = (
    selectinload(ModerationReview.question).selectinload(Question.author),
    selectinload(ModerationReview.answer).selectinload(Answer.author),
    selectinload(ModerationReview.answer).selectinload(Answer.question),
    selectinload(ModerationReview.reviewer),
)


def to_item(review: ModerationReview) -> ReviewItem:
    content = review.content
    if review.question is not None:
        kind, question = "question", review.question
    else:
        kind, question = "answer", review.answer.question
    return ReviewItem(
        id=review.id,
        kind=kind,
        question_id=question.id,
        question_title=question.title,
        body=content.body,
        author=content.author.username,
        reason=review.reason,
        status=content.status,
        created_at=review.created_at,
        reviewed_by=review.reviewer.username if review.reviewer else None,
        decided_at=review.decided_at,
    )


@router.get("/queue", response_model=list[ReviewItem])
def queue(
    content_status: Literal["pending", "rejected"] = Query("pending", alias="status"),
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    # Oldest first, so nothing sits in the queue forever.
    stmt = (
        select(ModerationReview)
        .outerjoin(Question, Question.id == ModerationReview.question_id)
        .outerjoin(Answer, Answer.id == ModerationReview.answer_id)
        .where(func.coalesce(Question.status, Answer.status) == content_status)
        .options(*LOAD_REVIEW)
        .order_by(ModerationReview.created_at, ModerationReview.id)
        .limit(100)
    )
    return [to_item(r) for r in db.scalars(stmt)]


@router.post("/reviews/{review_id}", response_model=ReviewItem)
def decide(
    review_id: int,
    data: ReviewDecision,
    moderator: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    review = db.get(ModerationReview, review_id, options=LOAD_REVIEW)
    if review is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Review not found")
    review.content.status = (
        ContentStatus.PUBLISHED if data.decision == "approve" else ContentStatus.REJECTED
    )
    review.reviewer = moderator
    review.decided_at = utcnow()
    db.commit()
    return to_item(review)
