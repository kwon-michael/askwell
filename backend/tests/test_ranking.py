from datetime import datetime, timedelta, timezone

from app.ranking import hot_score

NOW = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)


def hours_ago(h: float) -> datetime:
    return NOW - timedelta(hours=h)


def test_more_votes_wins_at_same_age():
    assert hot_score(10, hours_ago(5), NOW) > hot_score(2, hours_ago(5), NOW)


def test_newer_wins_at_same_votes():
    assert hot_score(5, hours_ago(1), NOW) > hot_score(5, hours_ago(24), NOW)


def test_fresh_answer_can_beat_stale_popular_one():
    assert hot_score(3, hours_ago(1), NOW) > hot_score(50, hours_ago(24 * 7), NOW)


def test_unvoted_answers_order_newest_first():
    assert hot_score(0, hours_ago(1), NOW) > hot_score(0, hours_ago(2), NOW)


def test_naive_datetime_treated_as_utc():
    naive = hours_ago(3).replace(tzinfo=None)
    assert hot_score(4, naive, NOW) == hot_score(4, hours_ago(3), NOW)


def test_future_timestamp_does_not_blow_up():
    # Clock skew between app servers shouldn't produce a negative age.
    assert hot_score(1, NOW + timedelta(minutes=5), NOW) == hot_score(1, NOW, NOW)
