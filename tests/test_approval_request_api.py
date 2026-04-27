"""Approval request API endpoint tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from swarmmind.api.supervisor import app
from swarmmind.db import dispose_engines, init_db
from swarmmind.repositories.approval_request import ApprovalRequestRepository
from swarmmind.repositories.project import ProjectRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "approval_api_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SWARMMIND_DB_INIT_MODE", "create_all")
    dispose_engines()
    init_db()


class TestApprovalRequestEndpoints:
    """Approval request REST API tests."""

    def test_list_approvals_empty(self):
        response = client.get("/approvals")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_create_approval(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")

        response = client.post(
            "/approvals",
            json={
                "project_id": proj.project_id,
                "title": "Deploy to production",
                "description": "High-risk deployment",
                "risk_tier": "high",
                "requested_capability": "deploy",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Deploy to production"
        assert data["risk_tier"] == "high"
        assert data["status"] == "pending"
        assert data["project_id"] == proj.project_id
        assert "approval_id" in data

    def test_create_approval_project_not_found(self):
        response = client.post(
            "/approvals",
            json={"project_id": "nonexistent", "title": "Deploy"},
        )
        assert response.status_code == 404

    def test_get_approval(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")
        ar_repo = ApprovalRequestRepository()
        ar = ar_repo.create(project_id=proj.project_id, title="Fetch Me")

        response = client.get(f"/approvals/{ar.approval_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Fetch Me"
        assert data["approval_id"] == ar.approval_id

    def test_get_approval_not_found(self):
        response = client.get("/approvals/nonexistent")
        assert response.status_code == 404

    def test_update_approval(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")
        ar_repo = ApprovalRequestRepository()
        ar = ar_repo.create(project_id=proj.project_id, title="Old Title")

        response = client.patch(
            f"/approvals/{ar.approval_id}",
            json={"title": "New Title", "status": "approved", "decision_reason": "Looks good"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"
        assert data["status"] == "approved"
        assert data["decision_reason"] == "Looks good"

    def test_update_approval_invalid_status_transition(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")
        ar_repo = ApprovalRequestRepository()
        ar = ar_repo.create(project_id=proj.project_id, title="Title", status="approved")

        response = client.patch(
            f"/approvals/{ar.approval_id}",
            json={"status": "rejected"},
        )
        assert response.status_code == 409

    def test_update_approval_not_found(self):
        response = client.patch(
            "/approvals/nonexistent",
            json={"title": "New Title"},
        )
        assert response.status_code == 404

    def test_delete_approval(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")
        ar_repo = ApprovalRequestRepository()
        ar = ar_repo.create(project_id=proj.project_id, title="To Delete")

        response = client.delete(f"/approvals/{ar.approval_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["approval_id"] == ar.approval_id

        response = client.get(f"/approvals/{ar.approval_id}")
        assert response.status_code == 404

    def test_delete_approval_not_found(self):
        response = client.delete("/approvals/nonexistent")
        assert response.status_code == 404

    def test_list_approvals_with_filters(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")
        ar_repo = ApprovalRequestRepository()
        ar_repo.create(project_id=proj.project_id, title="High Risk", risk_tier="high")
        ar_repo.create(project_id=proj.project_id, title="Low Risk", risk_tier="low")

        response = client.get(f"/approvals?project_id={proj.project_id}&risk_tier=high")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "High Risk"
