from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str
    is_admin: bool


class QuestionIn(BaseModel):
    title: str = Field(min_length=10, max_length=200)
    body: str = Field(default="", max_length=10_000)


class QuestionSummary(BaseModel):
    id: int
    title: str
    author: str
    created_at: datetime
    answer_count: int
    status: str


class AnswerIn(BaseModel):
    body: str = Field(min_length=1, max_length=20_000)


class AnswerOut(BaseModel):
    id: int
    body: str
    author: str
    created_at: datetime
    votes: int
    voted_by_me: bool
    status: str


class QuestionDetail(BaseModel):
    id: int
    title: str
    body: str
    author: str
    created_at: datetime
    answers: list[AnswerOut]


class VoteResult(BaseModel):
    answer_id: int
    votes: int
    voted_by_me: bool


class TopAnswer(BaseModel):
    answer_id: int
    question_id: int
    question_title: str
    author: str
    votes: int


class ReviewItem(BaseModel):
    id: int
    kind: Literal["question", "answer"]
    question_id: int
    question_title: str
    body: str
    author: str
    reason: str
    status: str
    created_at: datetime
    reviewed_by: str | None
    decided_at: datetime | None
    llm_verdict: str | None
    llm_reason: str | None


class ReviewDecision(BaseModel):
    decision: Literal["approve", "reject"]
