# Askwell

A Q&A community app: people ask questions, write answers, and upvote the good ones.
Built with FastAPI, PostgreSQL, and React + TypeScript.

## Status

- [x] Accounts (bcrypt passwords, JWT auth)
- [x] Questions, answers, upvotes
- [x] Answer ranking with time decay
- [x] "Top answers this week" report (raw SQL)
- [x] Tests + CI
- [x] Moderation pipeline (rule filter, then LLM classifier, then human review queue)
- [ ] A/B testing framework (hash-based bucketing, exposure and outcome events)
- [ ] Deploy

## Running locally

You need Python 3.11+, Node 20+, and Docker.

```bash
docker compose up -d                 # Postgres on :5434

cd backend
python -m venv .venv
.venv\Scripts\activate               # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head                 # create/upgrade the schema
uvicorn app.main:app --reload        # API on :8000, docs at /docs

cd ../frontend
npm install
npm run dev                          # app on :5173
```

The dev server proxies `/api/*` to the backend, so there's no CORS setup in development.

Schema changes go through Alembic: edit `app/models.py`, then
`alembic revision --autogenerate -m "..."` and review the generated file in
`migrations/versions/`. A test fails if the models and migrations drift apart.

The moderation classifier calls Claude, so it needs an Anthropic API key
(`$env:ANTHROPIC_API_KEY = "sk-ant-..."` in PowerShell before starting uvicorn).
Without one, everything still works: held posts just skip the classifier and go
straight to the review queue. `MODERATION_MODEL` picks the model
(default `claude-haiku-5-5`); set it to an empty string to turn the classifier off.

To see the review queue, make your account a moderator, then log in again
(a **Review** link appears in the header):

```bash
cd backend && python -m app.make_admin <username>     # --revoke to undo
```

If your local database predates migrations (it was created by the old
`create_all` on startup), run `alembic stamp 0001` once, then `alembic upgrade head`.

Tests run against in-memory SQLite and don't need Postgres:

```bash
cd backend && pytest
```

## Design notes

**Ranking.** Answers on a question are sorted by `(votes + 1) / (age_hours + 2) ^ 1.8`,
the same shape as Hacker News. A pure vote count makes the first decent answer
impossible to dislodge; decay gives later, better answers a chance. The gravity
constant is a guess for now. It's the first thing I plan to A/B test.
See [`backend/app/ranking.py`](backend/app/ranking.py).

**Top answers report.** Written as raw SQL instead of the ORM, and it only counts
votes cast inside the window, so an answer that was popular a month ago doesn't stay on top.
See [`backend/app/routers/answers.py`](backend/app/routers/answers.py).

**Moderation status.** Questions and answers carry a `status` (`pending`,
`published`, `rejected`). Every read path (feed, question page, top answers,
voting, answering) only sees `published` rows. The status is set on creation
by the rule filter in [`backend/app/moderation.py`](backend/app/moderation.py):
blocked spam phrases and more than three links are rejected outright; links from
accounts under a day old, mostly-capitals text, and long runs of one letter are
held as `pending`; everything else is published. Authors are told when their post
is held or rejected, but not which rule fired, so spammers can't tune against it.

**LLM classifier.** Posts the rules hold go to Claude in a background task
(the author gets an instant "under review" either way). It answers `allow`
(published), `remove` (rejected, still overturnable from the queue), or `unsure`
(left for a human, with the model's one-line note shown in the queue). Any failure
(no key, timeout, API error, refusal) also leaves the post for a human, so the
classifier can't publish anything by accident. The post is passed as delimited
data and the prompt tells the model to ignore instructions inside it, and the
response is constrained to a fixed schema. It runs on Claude Haiku 5.5 at low
effort: this is a short allow/remove/unsure call, and only held posts are
classified, so cost is a tiny fraction of a cent per held post.
See [`backend/app/classifier.py`](backend/app/classifier.py).

**Review queue.** Anything the rules don't approve gets a `moderation_reviews` row
with the reason. Moderators work through held content oldest-first and can also
browse rejected content to overturn false positives. The verdict lives on the
content itself; the review row records the rule's reason and who decided last.
See [`backend/app/routers/moderation.py`](backend/app/routers/moderation.py).

**Votes.** One row per (user, answer) with a unique constraint, so a race between
two double-clicks can't produce two votes. You can't vote on your own answer.

## API

| Method | Path | Auth |
| --- | --- | --- |
| POST | `/auth/register`, `/auth/login` | none |
| GET | `/auth/me` | required |
| GET | `/questions?sort=new\|active` | none |
| POST | `/questions` | required |
| GET | `/questions/{id}` | optional (fills `voted_by_me`) |
| POST | `/questions/{id}/answers` | required |
| POST | `/answers/{id}/vote` (toggles) | required |
| GET | `/answers/top?days=7` | none |
| GET | `/moderation/queue?status=pending\|rejected` | moderator |
| POST | `/moderation/reviews/{id}` (`approve` or `reject`) | moderator |
