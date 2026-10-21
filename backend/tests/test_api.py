from app.models import Answer, ContentStatus, Question


def ask(client, headers, title="How do B-trees stay balanced?"):
    res = client.post("/questions", json={"title": title, "body": ""}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def answer(client, headers, question_id, body="They split nodes on insert."):
    res = client.post(f"/questions/{question_id}/answers", json={"body": body}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_register_login_me(client):
    client.post("/auth/register", json={"username": "ada", "password": "password123"})
    res = client.post("/auth/login", json={"username": "ada", "password": "password123"})
    token = res.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["username"] == "ada"


def test_duplicate_username_rejected(client, make_user):
    make_user("ada")
    res = client.post("/auth/register", json={"username": "ada", "password": "password123"})
    assert res.status_code == 409


def test_wrong_password_rejected(client, make_user):
    make_user("ada")
    res = client.post("/auth/login", json={"username": "ada", "password": "wrongpassword"})
    assert res.status_code == 401


def test_posting_requires_login(client):
    res = client.post("/questions", json={"title": "A perfectly fine title", "body": ""})
    assert res.status_code == 401


def test_bad_token_rejected(client):
    res = client.get("/auth/me", headers={"Authorization": "Bearer nonsense"})
    assert res.status_code == 401


def test_question_feed_counts_answers(client, make_user):
    ada = make_user("ada")
    q1 = ask(client, ada, "First question about databases")
    ask(client, ada, "Second question about networks")
    answer(client, ada, q1)

    feed = client.get("/questions").json()
    assert [q["title"] for q in feed][0] == "Second question about networks"

    active = client.get("/questions?sort=active").json()
    assert active[0]["id"] == q1
    assert active[0]["answer_count"] == 1


def test_vote_toggles(client, make_user):
    ada, bob = make_user("ada"), make_user("bob")
    qid = ask(client, ada)
    aid = answer(client, ada, qid)

    first = client.post(f"/answers/{aid}/vote", headers=bob).json()
    assert first == {"answer_id": aid, "votes": 1, "voted_by_me": True}

    second = client.post(f"/answers/{aid}/vote", headers=bob).json()
    assert second == {"answer_id": aid, "votes": 0, "voted_by_me": False}


def test_cannot_vote_own_answer(client, make_user):
    ada = make_user("ada")
    aid = answer(client, ada, ask(client, ada))
    assert client.post(f"/answers/{aid}/vote", headers=ada).status_code == 400


def test_question_detail_ranks_by_votes_and_marks_my_votes(client, make_user):
    ada, bob, cat = make_user("ada"), make_user("bob"), make_user("cat")
    qid = ask(client, ada)
    weak = answer(client, bob, qid, "Magic.")
    strong = answer(client, cat, qid, "Splits and merges keep every leaf at the same depth.")
    client.post(f"/answers/{strong}/vote", headers=ada)
    client.post(f"/answers/{strong}/vote", headers=bob)

    detail = client.get(f"/questions/{qid}", headers=ada).json()
    ids = [a["id"] for a in detail["answers"]]
    assert ids == [strong, weak]
    assert detail["answers"][0]["voted_by_me"] is True
    assert detail["answers"][1]["voted_by_me"] is False


def test_top_answers(client, make_user):
    ada, bob = make_user("ada"), make_user("bob")
    qid = ask(client, ada)
    aid = answer(client, ada, qid)
    answer(client, ada, qid, "An answer nobody votes for.")
    client.post(f"/answers/{aid}/vote", headers=bob)

    top = client.get("/answers/top").json()
    assert len(top) == 1
    assert top[0]["answer_id"] == aid
    assert top[0]["votes"] == 1


def test_missing_question_404(client):
    assert client.get("/questions/999").status_code == 404


def set_status(db_session, model, id_, status):
    with db_session() as db:
        db.get(model, id_).status = status
        db.commit()


def test_unpublished_question_is_hidden(client, make_user, db_session):
    ada = make_user("ada")
    qid = ask(client, ada)
    set_status(db_session, Question, qid, ContentStatus.PENDING)

    assert client.get("/questions").json() == []
    assert client.get(f"/questions/{qid}").status_code == 404
    res = client.post(f"/questions/{qid}/answers", json={"body": "Hi"}, headers=ada)
    assert res.status_code == 404


def test_unpublished_answer_is_hidden(client, make_user, db_session):
    ada, bob = make_user("ada"), make_user("bob")
    qid = ask(client, ada)
    aid = answer(client, ada, qid)
    client.post(f"/answers/{aid}/vote", headers=bob)
    set_status(db_session, Answer, aid, ContentStatus.REJECTED)

    assert client.get(f"/questions/{qid}").json()["answers"] == []
    assert client.get("/questions").json()[0]["answer_count"] == 0
    assert client.get("/answers/top").json() == []
    assert client.post(f"/answers/{aid}/vote", headers=bob).status_code == 404


def test_clean_post_is_published(client, make_user):
    ada = make_user("ada")
    res = client.post("/questions", json={"title": "How do B-trees stay balanced?"}, headers=ada)
    assert res.json()["status"] == "published"


def test_spam_question_is_rejected_and_hidden(client, make_user):
    ada = make_user("ada")
    res = client.post(
        "/questions", json={"title": "Free crypto giveaway, click here"}, headers=ada
    )
    assert res.status_code == 201
    assert res.json()["status"] == "rejected"
    assert client.get("/questions").json() == []


def test_link_from_new_account_is_held_for_review(client, make_user):
    ada, bob = make_user("ada"), make_user("bob")
    qid = ask(client, ada)
    res = client.post(
        f"/questions/{qid}/answers", json={"body": "See https://example.com"}, headers=bob
    )
    assert res.json()["status"] == "pending"
    assert client.get(f"/questions/{qid}").json()["answers"] == []
