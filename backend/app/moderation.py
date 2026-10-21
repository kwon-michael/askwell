"""First stage of the moderation pipeline: cheap, deterministic rules.

Every new question and answer goes through check_rules(). Obvious spam is
rejected, clean text is published, and anything suspicious but not clear-cut
is escalated and waits as 'pending' in the review queue (routers/moderation.py)
until a moderator decides. An LLM classifier will later sit between the rules
and the queue, so people only see what the model is unsure about.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum

from sqlalchemy.orm import Session

from .models import Answer, ContentStatus, ModerationReview, Question, User, utcnow


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


def apply_rules(db: Session, content: Question | Answer, text: str, author: User) -> None:
    """Set the status of new content and, unless it's approved, record why."""
    result = check_rules(text, author.created_at)
    content.status = STATUS_FOR_VERDICT[result.verdict]
    if result.verdict is not Verdict.APPROVE:
        target = {"question": content} if isinstance(content, Question) else {"answer": content}
        db.add(ModerationReview(reason=result.reason, **target))
