import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.classifier import Classification, get_classifier
from app.db import Base, get_db, get_session_factory
from app.main import app


class FakeClassifier:
    """Stands in for Claude. Set .result to choose the verdict; None means
    the classifier couldn't decide (as on an API error)."""

    def __init__(self):
        self.result: Classification | None = None
        self.calls: list[tuple[str, str]] = []

    def __call__(self, text: str, flagged_because: str) -> Classification | None:
        self.calls.append((text, flagged_because))
        return self.result


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    yield Session
    engine.dispose()


@pytest.fixture
def classifier():
    return FakeClassifier()


@pytest.fixture
def client(db_session, classifier):
    def override_get_db():
        db = db_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_session_factory] = lambda: db_session
    # Never call the real API from tests.
    app.dependency_overrides[get_classifier] = lambda: classifier
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(client):
    def _make(username: str, password: str = "password123") -> dict:
        res = client.post("/auth/register", json={"username": username, "password": password})
        assert res.status_code == 201, res.text
        return {"Authorization": f"Bearer {res.json()['access_token']}"}

    return _make
