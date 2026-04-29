"""Audit log API endpoint tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from swarmmind.api.supervisor import app
from swarmmind.db import dispose_engines, init_db
from swarmmind.repositories.audit_log import AuditLogRepository
from swarmmind.repositories.project import ProjectRepository
from swarmmind.repositories.run import RunRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "audit_api_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    dispose_engines()
    init_db()


class TestAuditLogEndpoints:
    """Audit log REST API tests."""

    def test_list_audit_logs_empty(self):
        response = client.get("/audit-logs")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_create_audit_log(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")

        response = client.post(
            "/audit-logs",
            json={
                "project_id": proj.project_id,
                "audit_type": "approval_decision",
                "actor_id": "user-1",
                "actor_type": "user",
                "decision": "approved",
                "reason": "Looks good",
                "metadata": {"key": "value"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["audit_type"] == "approval_decision"
        assert data["project_id"] == proj.project_id
        assert data["actor_id"] == "user-1"
        assert data["decision"] == "approved"
        assert data["reason"] == "Looks good"
        assert data["metadata"] == {"key": "value"}
        assert "audit_id" in data

    def test_create_audit_log_project_not_found(self):
        response = client.post(
            "/audit-logs",
            json={"project_id": "nonexistent", "audit_type": "approval_decision"},
        )
        assert response.status_code == 404

    def test_get_audit_log(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")
        audit_repo = AuditLogRepository()
        entry = audit_repo.create(project_id=proj.project_id, decision="approved")

        response = client.get(f"/audit-logs/{entry.audit_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "approved"
        assert data["audit_id"] == entry.audit_id

    def test_get_audit_log_not_found(self):
        response = client.get("/audit-logs/nonexistent")
        assert response.status_code == 404

    def test_delete_audit_log(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")
        audit_repo = AuditLogRepository()
        entry = audit_repo.create(project_id=proj.project_id, decision="approved")

        response = client.delete(f"/audit-logs/{entry.audit_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["audit_id"] == entry.audit_id

        response = client.get(f"/audit-logs/{entry.audit_id}")
        assert response.status_code == 404

    def test_delete_audit_log_not_found(self):
        response = client.delete("/audit-logs/nonexistent")
        assert response.status_code == 404

    def test_list_project_audit_logs(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")
        audit_repo = AuditLogRepository()
        audit_repo.create(project_id=proj.project_id, decision="approved")
        audit_repo.create(project_id=proj.project_id, decision="rejected")

        response = client.get(f"/projects/{proj.project_id}/audit")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        decisions = {item["decision"] for item in data["items"]}
        assert decisions == {"approved", "rejected"}

    def test_list_project_audit_logs_project_not_found(self):
        response = client.get("/projects/nonexistent/audit")
        assert response.status_code == 404

    def test_list_audit_logs_with_filters(self):
        proj_repo = ProjectRepository()
        run_repo = RunRepository()
        proj = proj_repo.create(title="Test Project")
        run1 = run_repo.create(project_id=proj.project_id)
        audit_repo = AuditLogRepository()
        audit_repo.create(project_id=proj.project_id, decision="approved")
        audit_repo.create(project_id=proj.project_id, decision="rejected", run_id=run1.run_id)

        response = client.get(f"/audit-logs?project_id={proj.project_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

        response = client.get(f"/audit-logs?run_id={run1.run_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["decision"] == "rejected"
