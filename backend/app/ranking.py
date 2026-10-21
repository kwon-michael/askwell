"""Answer ranking.

Score decays with age so a new answer with a few votes can outrank an old one
with many. Same shape as the Hacker News formula: (votes + 1) / (age + 2)^gravity.
The +1 keeps unvoted answers from all tying at zero, so they fall back to
newest-first; the +2 keeps brand-new answers from getting an infinite boost.
"""

from datetime import datetime, timezone

DEFAULT_GRAVITY = 1.8


def hot_score(
    votes: int,
    created_at: datetime,
    now: datetime | None = None,
    gravity: float = DEFAULT_GRAVITY,
) -> float:
    now = now or datetime.now(timezone.utc)
    # SQLite hands back naive datetimes; everything we store is UTC.
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age_hours = max((now - created_at).total_seconds() / 3600, 0.0)
    return (votes + 1) / (age_hours + 2) ** gravity
