from datetime import datetime, timedelta, timezone

from app.moderation import Verdict, check_rules

NOW = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
OLD_ACCOUNT = NOW - timedelta(days=30)
NEW_ACCOUNT = NOW - timedelta(hours=1)


def verdict(text, created_at=OLD_ACCOUNT):
    return check_rules(text, created_at, now=NOW).verdict


def test_ordinary_text_is_approved():
    assert verdict("B-trees split full nodes on insert, so every leaf stays at one depth.") == Verdict.APPROVE


def test_blocked_term_is_rejected_regardless_of_case():
    result = check_rules("Huge CASINO BONUS today", OLD_ACCOUNT, now=NOW)
    assert result.verdict == Verdict.REJECT
    assert result.reason == "blocked term: casino bonus"


def test_too_many_links_is_rejected():
    text = " ".join(f"https://example.com/{i}" for i in range(4))
    assert verdict(text) == Verdict.REJECT


def test_a_few_links_from_an_established_account_are_fine():
    text = "See https://docs.python.org and https://peps.python.org/pep-0008/"
    assert verdict(text) == Verdict.APPROVE


def test_link_from_new_account_is_escalated():
    assert verdict("Check out www.example.com", NEW_ACCOUNT) == Verdict.ESCALATE


def test_shouting_is_escalated():
    assert verdict("WHY DOES NOBODY ANSWER MY QUESTION ABOUT THIS") == Verdict.ESCALATE


def test_short_acronyms_are_not_shouting():
    assert verdict("Use SQL, not ORM, for this.") == Verdict.APPROVE


def test_repeated_letters_are_escalated_but_markdown_rules_are_not():
    assert verdict("helloooooooooooo anyone") == Verdict.ESCALATE
    assert verdict("Part one\n\n----------\n\nPart two") == Verdict.APPROVE


def test_naive_timestamps_are_treated_as_utc():
    naive_new_account = NEW_ACCOUNT.replace(tzinfo=None)
    assert verdict("www.example.com", naive_new_account) == Verdict.ESCALATE
