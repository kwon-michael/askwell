from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from app.classifier import FALLBACK_BETA, Classification, ClaudeClassifier
from app.classifier import get_classifier

HELD_ANSWER = "See https://example.com for details"  # link from a new account


# --- The pipeline, with a fake classifier -------------------------------------


def ask(client, headers, title="How do B-trees stay balanced?"):
    return client.post("/questions", json={"title": title}, headers=headers).json()


def post_held_answer(client, make_user):
    ada, bob = make_user("ada"), make_user("bob")
    qid = ask(client, ada)["id"]
    res = client.post(f"/questions/{qid}/answers", json={"body": HELD_ANSWER}, headers=bob)
    assert res.json()["status"] == "pending"  # the author always sees "under review"
    return qid


def visible_answers(client, qid):
    return [a["body"] for a in client.get(f"/questions/{qid}").json()["answers"]]


def queue(client, make_user, db_session):
    from sqlalchemy import select

    from app.models import User

    mod = make_user("mod")
    with db_session() as db:
        db.scalar(select(User).where(User.username == "mod")).is_admin = True
        db.commit()
    return client.get("/moderation/queue", headers=mod).json()


def test_only_escalated_content_reaches_the_classifier(client, make_user, classifier):
    cat = make_user("cat")
    ask(client, cat)  # clean: published by the rules
    ask(client, cat, "Free crypto giveaway, click here")  # spam: rejected by the rules
    assert classifier.calls == []

    post_held_answer(client, make_user)
    assert classifier.calls == [(HELD_ANSWER, "link from a new account")]


def test_allow_publishes(client, make_user, classifier, db_session):
    classifier.result = Classification(verdict="allow", reason="A normal answer with a docs link.")
    qid = post_held_answer(client, make_user)

    assert visible_answers(client, qid) == [HELD_ANSWER]
    assert queue(client, make_user, db_session) == []


def test_remove_rejects(client, make_user, classifier, db_session):
    classifier.result = Classification(verdict="remove", reason="Link spam.")
    qid = post_held_answer(client, make_user)

    assert visible_answers(client, qid) == []
    assert queue(client, make_user, db_session) == []


def test_unsure_leaves_it_for_a_human_with_the_models_note(
    client, make_user, classifier, db_session
):
    classifier.result = Classification(verdict="unsure", reason="Could be self-promotion.")
    qid = post_held_answer(client, make_user)

    assert visible_answers(client, qid) == []
    [item] = queue(client, make_user, db_session)
    assert item["llm_verdict"] == "unsure"
    assert item["llm_reason"] == "Could be self-promotion."


def test_no_decision_leaves_it_for_a_human(client, make_user, classifier, db_session):
    classifier.result = None  # API down, refusal, no credentials, ...
    qid = post_held_answer(client, make_user)

    assert visible_answers(client, qid) == []
    [item] = queue(client, make_user, db_session)
    assert item["llm_verdict"] is None


def test_classifier_crash_leaves_it_for_a_human(client, make_user, db_session):
    from app.classifier import get_classifier as dep
    from app.main import app

    def broken(text, flagged_because):
        raise TypeError("Could not resolve authentication method")

    app.dependency_overrides[dep] = lambda: broken
    qid = post_held_answer(client, make_user)

    assert visible_answers(client, qid) == []
    [item] = queue(client, make_user, db_session)
    assert item["status"] == "pending"


def test_classifier_can_be_turned_off(monkeypatch):
    monkeypatch.setattr("app.classifier.MODERATION_MODEL", "")
    assert get_classifier() is None


# --- ClaudeClassifier itself, with a stubbed SDK client -----------------------


class StubMessages:
    def __init__(self, outcome):
        self.outcome = outcome
        self.kwargs = None

    def parse(self, **kwargs):
        self.kwargs = kwargs
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def stub_client(outcome):
    messages = StubMessages(outcome)
    return SimpleNamespace(beta=SimpleNamespace(messages=messages)), messages


def response(stop_reason="end_turn", parsed=None):
    return SimpleNamespace(stop_reason=stop_reason, parsed_output=parsed, _request_id="req_test")


def test_returns_the_parsed_classification():
    verdict = Classification(verdict="allow", reason="Fine.")
    client, messages = stub_client(response(parsed=verdict))

    assert ClaudeClassifier("claude-opus-5-5", client)("hello", "mostly capital letters") == verdict
    sent = messages.kwargs
    assert sent["model"] == "claude-opus-5-5"
    assert sent["output_format"] is Classification
    assert sent["output_config"] == {"effort": "low"}
    assert "mostly capital letters" in sent["messages"][0]["content"]
    assert "<post>\nhello\n</post>" in sent["messages"][0]["content"]


def test_opts_into_refusal_fallbacks_where_supported():
    _, opus = stub_client(response(parsed=Classification(verdict="allow", reason=".")))
    ClaudeClassifier("claude-opus-5-5", SimpleNamespace(beta=SimpleNamespace(messages=opus)))("x", "r")
    assert opus.kwargs["fallbacks"] == "default"
    assert opus.kwargs["betas"] == [FALLBACK_BETA]

    _, haiku = stub_client(response(parsed=Classification(verdict="allow", reason=".")))
    ClaudeClassifier("claude-haiku-5-5", SimpleNamespace(beta=SimpleNamespace(messages=haiku)))("x", "r")
    assert "fallbacks" not in haiku.kwargs


@pytest.mark.parametrize(
    "outcome",
    [
        response(stop_reason="refusal"),
        response(stop_reason="max_tokens"),
        response(parsed=None),
    ],
    ids=["refusal", "max_tokens", "unparsed"],
)
def test_unusable_responses_mean_no_decision(outcome):
    client, _ = stub_client(outcome)
    assert ClaudeClassifier("claude-opus-5-5", client)("x", "r") is None


REQUEST = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


@pytest.mark.parametrize(
    "error",
    [
        anthropic.APITimeoutError(request=REQUEST),
        anthropic.APIConnectionError(request=REQUEST),
        anthropic.RateLimitError(
            "slow down", response=httpx2.Response(429, request=REQUEST), body=None
        ),
        anthropic.InternalServerError(
            "oops", response=httpx2.Response(500, request=REQUEST), body=None
        ),
        anthropic.AuthenticationError(
            "bad key", response=httpx2.Response(401, request=REQUEST), body=None
        ),
    ],
    ids=["timeout", "connection", "rate_limit", "server_error", "auth"],
)
def test_api_errors_mean_no_decision(error):
    client, _ = stub_client(error)
    assert ClaudeClassifier("claude-opus-5-5", client)("x", "r") is None
