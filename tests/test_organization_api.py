"""Organization, team, and team membership API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from swarmmind.api.supervisor import app
from swarmmind.db import dispose_engines, init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "organization_api_test.db"
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


def test_organization_crud() -> None:
    headers = _admin_headers()
    owner = _create_user("owner@example.com", headers)

    created = client.post(
        "/organizations",
        json={"name": "Acme", "owner_user_id": owner["user_id"]},
        headers=headers,
    )
    assert created.status_code == 201
    org = created.json()
    assert org["name"] == "Acme"
    assert org["owner_user_id"] == owner["user_id"]

    listed = client.get("/organizations", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    fetched = client.get(f"/organizations/{org['organization_id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Acme"

    updated = client.patch(
        f"/organizations/{org['organization_id']}",
        json={"name": "Acme Inc."},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Acme Inc."

    deleted = client.delete(f"/organizations/{org['organization_id']}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "archived"


def test_team_crud() -> None:
    headers = _admin_headers()
    owner = _create_user("owner2@example.com", headers)
    org = client.post(
        "/organizations",
        json={"name": "Acme", "owner_user_id": owner["user_id"]},
        headers=headers,
    ).json()

    created = client.post(
        f"/organizations/{org['organization_id']}/teams",
        json={"name": "Platform"},
        headers=headers,
    )
    assert created.status_code == 201
    team = created.json()
    assert team["name"] == "Platform"

    listed = client.get(f"/organizations/{org['organization_id']}/teams", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    fetched = client.get(f"/teams/{team['team_id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Platform"

    updated = client.patch(
        f"/teams/{team['team_id']}",
        json={"name": "Platform Team"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Platform Team"

    deleted = client.delete(f"/teams/{team['team_id']}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "archived"


def test_team_membership_crud() -> None:
    headers = _admin_headers()
    owner = _create_user("owner3@example.com", headers)
    member = _create_user("member@example.com", headers)
    org = client.post(
        "/organizations",
        json={"name": "Acme", "owner_user_id": owner["user_id"]},
        headers=headers,
    ).json()
    team = client.post(
        f"/organizations/{org['organization_id']}/teams",
        json={"name": "Engineering"},
        headers=headers,
    ).json()

    created = client.post(
        f"/teams/{team['team_id']}/members",
        json={"user_id": member["user_id"], "role": "member"},
        headers=headers,
    )
    assert created.status_code == 201
    membership = created.json()
    assert membership["user_id"] == member["user_id"]

    listed = client.get(f"/teams/{team['team_id']}/members", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    updated = client.patch(
        f"/teams/{team['team_id']}/members/{membership['membership_id']}",
        json={"role": "admin"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["role"] == "admin"

    removed = client.delete(
        f"/teams/{team['team_id']}/members/{membership['membership_id']}",
        headers=headers,
    )
    assert removed.status_code == 200
    assert removed.json()["status"] == "removed"


def test_organization_requires_admin() -> None:
    headers = _admin_headers()
    member = _create_user("member4@example.com", headers)
    login = client.post(
        "/auth/login",
        json={"email": member["email"], "password": "password"},
    )
    assert login.status_code == 200
    member_headers = {"Authorization": f"Bearer {login.json()['token']}"}

    response = client.get("/organizations", headers=member_headers)
    assert response.status_code == 403
