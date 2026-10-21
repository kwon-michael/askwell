import pytest
from sqlalchemy import select

from app.make_admin import main as make_admin
from app.models import User

HELD_ANSWER = "See https://example.com for details"  # link from a new account
SPAM_TITLE = "Free crypto giveaway, click here"


@pytest.fixture
def make_admin_user(make_user, db_session):
    def _make(username: str) -> dict:
        headers = make_user(username)
        with db_session() as db:
            db.scalar(select(User).where(User.username == username)).is_admin = True
            db.commit()
        return headers

    return _make


def ask(client, headers, title="How do B-trees stay balanced?"):
    return client.post("/questions", json={"title": title}, headers=headers).json()


def answer(client, headers, question_id, body):
    return client.post(
        f"/questions/{question_id}/answers", json={"body": body}, headers=headers
    ).json()


def test_queue_is_for_moderators_only(client, make_user):
    ada = make_user("ada")
    assert client.get("/moderation/queue").status_code == 401
    assert client.get("/moderation/queue", headers=ada).status_code == 403
    res = client.post("/moderation/reviews/1", json={"decision": "approve"}, headers=ada)
    assert res.status_code == 403


def test_me_reports_admin_flag(client, make_user, make_admin_user):
    assert client.get("/auth/me", headers=make_user("ada")).json()["is_admin"] is False
    assert client.get("/auth/me", headers=make_admin_user("mod")).json()["is_admin"] is True


def test_held_answer_shows_in_queue_with_context(client, make_user, make_admin_user):
    ada, bob, mod = make_user("ada"), make_user("bob"), make_admin_user("mod")
    q = ask(client, ada)
    answer(client, bob, q["id"], HELD_ANSWER)

    [item] = client.get("/moderation/queue", headers=mod).json()
    assert item["kind"] == "answer"
    assert item["question_id"] == q["id"]
    assert item["question_title"] == q["title"]
    assert item["body"] == HELD_ANSWER
    assert item["author"] == "bob"
    assert item["reason"] == "link from a new account"
    assert item["status"] == "pending"
    assert item["reviewed_by"] is None


def test_approving_publishes_and_leaves_the_queue(client, make_user, make_admin_user):
    ada, bob, mod = make_user("ada"), make_user("bob"), make_admin_user("mod")
    qid = ask(client, ada)["id"]
    answer(client, bob, qid, HELD_ANSWER)
    [item] = client.get("/moderation/queue", headers=mod).json()

    res = client.post(
        f"/moderation/reviews/{item['id']}", json={"decision": "approve"}, headers=mod
    )
    assert res.json()["status"] == "published"
    assert res.json()["reviewed_by"] == "mod"

    assert client.get("/moderation/queue", headers=mod).json() == []
    assert [a["body"] for a in client.get(f"/questions/{qid}").json()["answers"]] == [HELD_ANSWER]


def test_rejecting_keeps_it_hidden(client, make_user, make_admin_user):
    ada, mod = make_user("ada"), make_admin_user("mod")
    ask(client, ada, "WHY DOES NOBODY ANSWER MY QUESTIONS")
    [item] = client.get("/moderation/queue", headers=mod).json()
    assert item["kind"] == "question"

    client.post(f"/moderation/reviews/{item['id']}", json={"decision": "reject"}, headers=mod)

    assert client.get("/moderation/queue", headers=mod).json() == []
    assert client.get("/questions").json() == []
    rejected = client.get("/moderation/queue?status=rejected", headers=mod).json()
    assert [r["id"] for r in rejected] == [item["id"]]


def test_false_positive_spam_can_be_overturned(client, make_user, make_admin_user):
    ada, mod = make_user("ada"), make_admin_user("mod")
    q = ask(client, ada, SPAM_TITLE)
    assert q["status"] == "rejected"
    assert client.get("/moderation/queue", headers=mod).json() == []

    [item] = client.get("/moderation/queue?status=rejected", headers=mod).json()
    assert item["reason"] == "blocked term: crypto giveaway"
    client.post(f"/moderation/reviews/{item['id']}", json={"decision": "approve"}, headers=mod)

    assert client.get(f"/questions/{q['id']}").status_code == 200


def test_approved_content_gets_no_review(client, make_user, make_admin_user):
    ada, mod = make_user("ada"), make_admin_user("mod")
    ask(client, ada)
    assert client.get("/moderation/queue", headers=mod).json() == []
    assert client.get("/moderation/queue?status=rejected", headers=mod).json() == []


def test_unknown_review_404(client, make_admin_user):
    mod = make_admin_user("mod")
    res = client.post("/moderation/reviews/999", json={"decision": "approve"}, headers=mod)
    assert res.status_code == 404


def test_make_admin_command(make_user, db_session, monkeypatch, capsys):
    make_user("ada")
    monkeypatch.setattr("app.make_admin.SessionLocal", db_session)

    assert make_admin(["ada"]) == 0
    with db_session() as db:
        assert db.scalar(select(User.is_admin).where(User.username == "ada")) is True

    assert make_admin(["ada", "--revoke"]) == 0
    with db_session() as db:
        assert db.scalar(select(User.is_admin).where(User.username == "ada")) is False

    assert make_admin(["nobody"]) == 1
    assert make_admin([]) == 2
