"""User resource allocation API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from swarmmind.api.supervisor import app
from swarmmind.db import dispose_engines, init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "user_allocation_api_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    dispose_engines()
    init_db()


def _admin_headers(password: str = "admin") -> dict:  # noqa: S107
    response = client.post(
        "/auth/setup",
        json={"email": "admin@example.com", "password": password, "username": "admin"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['token']}"}


def _create_user(email: str, headers: dict) -> dict:
    response = client.post(
        "/users",
        json={"email": email, "password": "password", "role": "member"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_user_allocation_crud() -> None:
    headers = _admin_headers()
    user = _create_user("user@example.com", headers)

    set_model = client.put(
        f"/admin/users/{user['user_id']}/allocations",
        json={"resource_type": "model", "resource_name": "gpt-4o", "is_allowed": True},
        headers=headers,
    )
    assert set_model.status_code == 200
    allocation = set_model.json()
    assert allocation["resource_type"] == "model"
    assert allocation["resource_name"] == "gpt-4o"
    assert allocation["is_allowed"] is True

    set_mcp = client.put(
        f"/admin/users/{user['user_id']}/allocations",
        json={"resource_type": "mcp", "resource_name": "filesystem", "is_allowed": True},
        headers=headers,
    )
    assert set_mcp.status_code == 200

    listed = client.get(f"/admin/users/{user['user_id']}/allocations", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 2

    deleted = client.delete(
        f"/admin/users/{user['user_id']}/allocations",
        params={"resource_type": "model", "resource_name": "gpt-4o"},
        headers=headers,
    )
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"

    listed = client.get(f"/admin/users/{user['user_id']}/allocations", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1


def test_user_allocation_requires_admin() -> None:
    headers = _admin_headers()
    user = _create_user("member@example.com", headers)
    login = client.post(
        "/auth/login",
        json={"email": user["email"], "password": "password"},
    )
    assert login.status_code == 200
    member_headers = {"Authorization": f"Bearer {login.json()['token']}"}

    response = client.get(
        f"/admin/users/{user['user_id']}/allocations",
        headers=member_headers,
    )
    assert response.status_code == 403
