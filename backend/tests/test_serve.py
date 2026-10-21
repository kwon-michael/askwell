import pytest
from fastapi.testclient import TestClient

from app.config import sqlalchemy_url
from app.serve import create_app


@pytest.fixture
def prod_client(tmp_path, client):  # `client` installs the test DB overrides
    (tmp_path / "index.html").write_text("<html>askwell</html>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)")
    return TestClient(create_app(tmp_path))


def test_api_is_served_under_api(prod_client):
    assert prod_client.get("/api/health").json() == {"status": "ok"}
    assert prod_client.get("/api/questions").json() == []


def test_frontend_assets_and_index(prod_client):
    assert prod_client.get("/").text == "<html>askwell</html>"
    assert prod_client.get("/assets/app.js").text == "console.log(1)"


def test_client_side_routes_fall_back_to_index(prod_client):
    res = prod_client.get("/q/42")
    assert res.status_code == 200
    assert res.text == "<html>askwell</html>"


@pytest.mark.parametrize(
    "given, expected",
    [
        ("postgres://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("postgresql://u:p@host/db?sslmode=require", "postgresql+psycopg://u:p@host/db?sslmode=require"),
        ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("sqlite://", "sqlite://"),
    ],
)
def test_hosted_database_urls_use_psycopg3(given, expected):
    assert sqlalchemy_url(given) == expected
