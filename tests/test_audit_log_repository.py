"""Audit log repository tests."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from swarmmind.db import dispose_engines, init_db
from swarmmind.repositories.audit_log import AuditLogRepository
from swarmmind.repositories.project import ProjectRepository
from swarmmind.repositories.run import RunRepository


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "audit_repo_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SWARMMIND_DB_INIT_MODE", "create_all")
    dispose_engines()
    init_db()


@pytest.fixture
def audit_repo():
    return AuditLogRepository()


class TestAuditLogRepository:
    """Audit log CRUD tests."""

    def test_create_and_get(self, audit_repo):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")

        entry = audit_repo.create(
            project_id=proj.project_id,
            audit_type="approval_decision",
            actor_id="user-1",
            actor_type="user",
            decision="approved",
            reason="Looks good",
            extra_data={"key": "value"},
        )
        assert entry.audit_type == "approval_decision"
        assert entry.project_id == proj.project_id
        assert entry.actor_id == "user-1"
        assert entry.decision == "approved"
        assert entry.reason == "Looks good"
        assert entry.extra_data == {"key": "value"}

        fetched = audit_repo.get(entry.audit_id)
        assert fetched.audit_id == entry.audit_id
        assert fetched.decision == "approved"

    def test_list_by_project(self, audit_repo):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")

        audit_repo.create(project_id=proj.project_id, decision="approved")
        audit_repo.create(project_id=proj.project_id, decision="rejected")

        results = audit_repo.list_by_project(proj.project_id)
        assert len(results) == 2
        decisions = {r.decision for r in results}
        assert decisions == {"approved", "rejected"}

    def test_list_by_filters(self, audit_repo):
        proj_repo = ProjectRepository()
        run_repo = RunRepository()
        proj = proj_repo.create(title="Test Project")
        proj2 = proj_repo.create(title="Other Project")
        run1 = run_repo.create(project_id=proj.project_id)

        audit_repo.create(project_id=proj.project_id, decision="approved")
        audit_repo.create(project_id=proj.project_id, decision="rejected", run_id=run1.run_id)
        audit_repo.create(project_id=proj2.project_id, decision="approved")

        results = audit_repo.list_by_filters(project_id=proj.project_id)
        assert len(results) == 2

        results = audit_repo.list_by_filters(run_id=run1.run_id)
        assert len(results) == 1
        assert results[0].decision == "rejected"

        results = audit_repo.list_by_filters()
        assert len(results) == 3

    def test_delete(self, audit_repo):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")
        entry = audit_repo.create(project_id=proj.project_id, decision="approved")

        audit_repo.delete(entry.audit_id)

        with pytest.raises(HTTPException):
            audit_repo.get(entry.audit_id)

    def test_get_not_found(self, audit_repo):
        with pytest.raises(HTTPException):
            audit_repo.get("nonexistent")
