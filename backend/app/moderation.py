"""First stage of the moderation pipeline: cheap, deterministic rules.

Every new question and answer goes through check_rules(). Obvious spam is
rejected, clean text is published, and anything suspicious but not clear-cut
is escalated and waits as 'pending'. Escalated content then goes to the LLM
classifier (classifier.py) in a background task, which decides the clear cases;
whatever it can't decide stays in the human review queue (routers/moderation.py).
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum

from sqlalchemy.orm import Session, sessionmaker

from .classifier import Classifier
from .models import Answer, ContentStatus, ModerationReview, Question, User, utcnow

log = logging.getLogger(__name__)


class Verdict(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class RuleResult:
    verdict: Verdict
    reason: str | None = None


# Phrases that only show up in spam. Matched case-insensitively as substrings.
BLOCKED_TERMS = (
    "casino bonus",
    "crypto giveaway",
    "buy followers",
    "whatsapp me",
    "telegram me",
)
MAX_LINKS = 3
NEW_ACCOUNT_AGE = timedelta(hours=24)
SHOUTING_MIN_LETTERS = 20
SHOUTING_RATIO = 0.7

URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)
# Letters only, so markdown rules (----------) and code don't trip it.
REPEATED_LETTER_RE = re.compile(r"([a-z])\1{9,}", re.IGNORECASE)

STATUS_FOR_VERDICT = {
    Verdict.APPROVE: ContentStatus.PUBLISHED,
    Verdict.REJECT: ContentStatus.REJECTED,
    Verdict.ESCALATE: ContentStatus.PENDING,
}


def check_rules(text: str, author_created_at: datetime, now: datetime | None = None) -> RuleResult:
    now = now or utcnow()
    if author_created_at.tzinfo is None:
        # SQLite (used in tests) drops the timezone; we always store UTC.
        author_created_at = author_created_at.replace(tzinfo=timezone.utc)

    lowered = text.lower()
    for term in BLOCKED_TERMS:
        if term in lowered:
            return RuleResult(Verdict.REJECT, f"blocked term: {term}")

    links = len(URL_RE.findall(text))
    if links > MAX_LINKS:
        return RuleResult(Verdict.REJECT, f"too many links ({links})")
    if links and now - author_created_at < NEW_ACCOUNT_AGE:
        return RuleResult(Verdict.ESCALATE, "link from a new account")

    letters = [c for c in text if c.isalpha()]
    if len(letters) >= SHOUTING_MIN_LETTERS:
        upper = sum(c.isupper() for c in letters)
        if upper / len(letters) >= SHOUTING_RATIO:
            return RuleResult(Verdict.ESCALATE, "mostly capital letters")

    if REPEATED_LETTER_RE.search(text):
        return RuleResult(Verdict.ESCALATE, "long run of a repeated letter")

    return RuleResult(Verdict.APPROVE)


def apply_rules(
    db: Session, content: Question | Answer, text: str, author: User
) -> ModerationReview | None:
    """Set the status of new content and, unless it's approved, record why.

    Returns the review if the content was escalated, so the caller can hand
    it to the classifier once it's committed.
    """
    result = check_rules(text, author.created_at)
    content.status = STATUS_FOR_VERDICT[result.verdict]
    if result.verdict is Verdict.APPROVE:
        return None
    target = {"question": content} if isinstance(content, Question) else {"answer": content}
    review = ModerationReview(reason=result.reason, **target)
    db.add(review)
    return review if result.verdict is Verdict.ESCALATE else None


LLM_STATUS = {"allow": ContentStatus.PUBLISHED, "remove": ContentStatus.REJECTED}


def classify_review(session_factory: sessionmaker, classifier: Classifier, review_id: int) -> None:
    """Background task: let the LLM decide an escalated post if it can."""
    with session_factory() as db:
        review = db.get(ModerationReview, review_id)
        # A moderator may have got to it first.
        if review is None or review.content.status != ContentStatus.PENDING:
            return
        try:
            result = classifier(review.content_text, review.reason)
        except Exception:
            # e.g. the SDK raises TypeError when no credentials are configured.
            # Whatever went wrong, the post just waits for a human.
            log.exception("classifier: failed on review %s", review_id)
            return
        if result is None:
            return
        review.llm_verdict = result.verdict
        review.llm_reason = result.reason[:500]
        if result.verdict in LLM_STATUS:
            review.content.status = LLM_STATUS[result.verdict]
        db.commit()
        log.info("classifier: review %s -> %s (%s)", review_id, result.verdict, result.reason)
