"""User and auth API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from swarmmind.api.supervisor import app
from swarmmind.db import dispose_engines, init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "user_api_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    dispose_engines()
    init_db()


def _create_user(email: str = "Ada@Example.COM", password: str = "correct horse") -> dict:  # noqa: S107
    response = client.post(
        "/users",
        json={"email": email, "password": password, "display_name": "Ada", "role": "admin"},
    )
    assert response.status_code == 201
    return response.json()


def test_create_list_and_get_user() -> None:
    created = _create_user()

    assert created["email"] == "ada@example.com"
    assert created["display_name"] == "Ada"
    assert created["role"] == "admin"
    assert "password_hash" not in created

    listed = client.get("/users")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    fetched = client.get(f"/users/{created['user_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["email"] == "ada@example.com"


def test_duplicate_email_returns_409() -> None:
    _create_user()

    response = client.post("/users", json={"email": "ada@example.com", "password": "correct horse"})

    assert response.status_code == 409


def test_login_me_and_logout_token_cycle() -> None:
    _create_user()

    login = client.post(
        "/auth/login", json={"email": "ada@example.com", "password": "correct horse", "token_name": "cli"}
    )

    assert login.status_code == 200
    token_data = login.json()
    assert token_data["token"].startswith("swm_")
    assert token_data["user"]["email"] == "ada@example.com"

    headers = {"Authorization": f"Bearer {token_data['token']}"}
    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "ada@example.com"
    assert me.json()["token_id"] == token_data["token_id"]

    logout = client.post("/auth/logout", headers=headers)
    assert logout.status_code == 200
    assert logout.json()["status"] == "revoked"

    revoked = client.get("/auth/me", headers=headers)
    assert revoked.status_code == 401


def test_login_rejects_wrong_password_and_disabled_user() -> None:
    user = _create_user()

    wrong = client.post("/auth/login", json={"email": "ada@example.com", "password": "wrong"})
    assert wrong.status_code == 401

    disabled = client.delete(f"/users/{user['user_id']}")
    assert disabled.status_code == 200

    login = client.post("/auth/login", json={"email": "ada@example.com", "password": "correct horse"})
    assert login.status_code == 403


def test_disabling_user_revokes_active_tokens() -> None:
    user = _create_user()
    login = client.post("/auth/login", json={"email": "ada@example.com", "password": "correct horse"})
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/auth/me", headers=headers).status_code == 200
    assert client.delete(f"/users/{user['user_id']}").status_code == 200

    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 401
