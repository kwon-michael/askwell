"""First stage of the moderation pipeline: cheap, deterministic rules.

Every new question and answer goes through check_rules(). Obvious spam is
rejected, clean text is published, and anything suspicious but not clear-cut
is escalated and waits as 'pending'. Later stages (an LLM classifier, then a
human review queue) will decide what happens to escalated content.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum

from .models import ContentStatus, User, utcnow

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


def initial_status(text: str, author: User) -> ContentStatus:
    result = check_rules(text, author.created_at)
    if result.verdict is not Verdict.APPROVE:
        log.info("moderation: %s by user %s (%s)", result.verdict, author.id, result.reason)
    return STATUS_FOR_VERDICT[result.verdict]
