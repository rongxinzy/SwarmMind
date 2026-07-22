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


def _create_admin(email: str = "admin@example.com", password: str = "admin") -> dict:  # noqa: S107
    response = client.post("/auth/setup", json={"email": email, "password": password, "username": "admin"})
    assert response.status_code == 201
    return response.json()


def _admin_headers(email: str = "admin@example.com", password: str = "admin") -> dict:  # noqa: S107
    admin = _create_admin(email, password)
    return {"Authorization": f"Bearer {admin['token']}"}


def _create_user(email: str = "Ada@Example.COM", password: str = "correct horse", headers=None) -> dict:  # noqa: S107
    if headers is None:
        headers = _admin_headers()
    response = client.post(
        "/users",
        json={"email": email, "password": password, "display_name": "Ada", "role": "member"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_create_list_and_get_user() -> None:
    headers = _admin_headers()
    created = _create_user(headers=headers)

    assert created["email"] == "ada@example.com"
    assert created["display_name"] == "Ada"
    assert created["role"] == "member"
    assert "password_hash" not in created

    listed = client.get("/users", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 2  # admin + member

    fetched = client.get(f"/users/{created['user_id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["email"] == "ada@example.com"


def test_create_user_requires_admin() -> None:
    headers = _admin_headers()
    member = _create_user(headers=headers)
    member_login = client.post(
        "/auth/login", json={"email": member["email"], "password": "correct horse"}
    )
    assert member_login.status_code == 200
    member_headers = {"Authorization": f"Bearer {member_login.json()['token']}"}

    response = client.post(
        "/users",
        json={"email": "new@example.com", "password": "password"},
        headers=member_headers,
    )
    assert response.status_code == 403


def test_duplicate_email_returns_409() -> None:
    headers = _admin_headers()
    _create_user(headers=headers)

    response = client.post("/users", json={"email": "ada@example.com", "password": "correct horse"}, headers=headers)

    assert response.status_code == 409


def test_login_me_and_logout_token_cycle() -> None:
    headers = _admin_headers()
    user = _create_user(headers=headers)

    login = client.post(
        "/auth/login", json={"email": user["email"], "password": "correct horse", "token_name": "cli"}
    )

    assert login.status_code == 200
    token_data = login.json()
    assert token_data["token"].startswith("swm_")
    assert token_data["user"]["email"] == "ada@example.com"

    me_headers = {"Authorization": f"Bearer {token_data['token']}"}
    me = client.get("/auth/me", headers=me_headers)
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "ada@example.com"
    assert me.json()["token_id"] == token_data["token_id"]

    logout = client.post("/auth/logout", headers=me_headers)
    assert logout.status_code == 200
    assert logout.json()["status"] == "revoked"

    revoked = client.get("/auth/me", headers=me_headers)
    assert revoked.status_code == 401


def test_login_rejects_wrong_password_and_disabled_user() -> None:
    headers = _admin_headers()
    user = _create_user(headers=headers)

    wrong = client.post("/auth/login", json={"email": user["email"], "password": "wrong"})
    assert wrong.status_code == 401

    disabled = client.delete(f"/users/{user['user_id']}", headers=headers)
    assert disabled.status_code == 200

    login = client.post("/auth/login", json={"email": user["email"], "password": "correct horse"})
    assert login.status_code == 403


def test_disabling_user_revokes_active_tokens() -> None:
    headers = _admin_headers()
    user = _create_user(headers=headers)
    login = client.post("/auth/login", json={"email": user["email"], "password": "correct horse"})
    token = login.json()["token"]
    me_headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/auth/me", headers=me_headers).status_code == 200
    assert client.delete(f"/users/{user['user_id']}", headers=headers).status_code == 200

    response = client.get("/auth/me", headers=me_headers)
    assert response.status_code == 401
