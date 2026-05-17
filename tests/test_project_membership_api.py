"""Project membership API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from swarmmind.api.supervisor import app
from swarmmind.db import dispose_engines, init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "project_membership_api_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    dispose_engines()
    init_db()


def _project_id() -> str:
    response = client.post("/projects", json={"title": "Governed Project"})
    assert response.status_code == 200
    return response.json()["project_id"]


def test_add_list_and_get_project_member() -> None:
    project_id = _project_id()

    created = client.post(
        f"/projects/{project_id}/members",
        json={"member_id": "user-1", "display_name": "User One", "role": "owner"},
    )

    assert created.status_code == 201
    data = created.json()
    assert data["member_id"] == "user-1"
    assert data["role"] == "owner"
    assert "manage_members" in data["capabilities"]

    listed = client.get(f"/projects/{project_id}/members")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    fetched = client.get(f"/projects/{project_id}/members/user-1")
    assert fetched.status_code == 200
    assert fetched.json()["membership_id"] == data["membership_id"]


def test_duplicate_project_member_returns_409() -> None:
    project_id = _project_id()
    body = {"member_id": "user-1", "role": "viewer"}
    assert client.post(f"/projects/{project_id}/members", json=body).status_code == 201

    response = client.post(f"/projects/{project_id}/members", json=body)

    assert response.status_code == 409


def test_update_member_and_permission_check() -> None:
    project_id = _project_id()
    client.post(f"/projects/{project_id}/members", json={"member_id": "approver-1", "role": "viewer"})

    denied = client.get(f"/projects/{project_id}/members/approver-1/permissions/approve_high_risk")
    assert denied.status_code == 200
    assert denied.json()["allowed"] is False

    updated = client.patch(f"/projects/{project_id}/members/approver-1", json={"role": "approver"})
    assert updated.status_code == 200
    assert updated.json()["role"] == "approver"

    allowed = client.get(f"/projects/{project_id}/members/approver-1/permissions/approve_high_risk")
    assert allowed.status_code == 200
    assert allowed.json()["allowed"] is True


def test_inactive_member_loses_capabilities() -> None:
    project_id = _project_id()
    client.post(f"/projects/{project_id}/members", json={"member_id": "editor-1", "role": "editor"})

    updated = client.patch(f"/projects/{project_id}/members/editor-1", json={"status": "inactive"})

    assert updated.status_code == 200
    assert updated.json()["capabilities"] == []
    response = client.get(f"/projects/{project_id}/members/editor-1/permissions/run_project")
    assert response.json()["allowed"] is False
    assert response.json()["reason"] == "member_inactive"


def test_member_changes_write_audit_log() -> None:
    project_id = _project_id()

    client.post(f"/projects/{project_id}/members", json={"member_id": "user-1", "role": "viewer"})
    client.patch(f"/projects/{project_id}/members/user-1", json={"role": "editor"})
    client.delete(f"/projects/{project_id}/members/user-1")

    audit = client.get(f"/projects/{project_id}/audit")
    assert audit.status_code == 200
    audit_types = [item["audit_type"] for item in audit.json()["items"]]
    assert "member.added" in audit_types
    assert "member.updated" in audit_types
    assert "member.removed" in audit_types
