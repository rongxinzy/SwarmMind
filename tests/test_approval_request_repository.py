"""Approval request repository tests."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from swarmmind.db import dispose_engines, init_db
from swarmmind.repositories.approval_request import ApprovalRequestRepository
from swarmmind.repositories.project import ProjectRepository


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "approval_repo_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SWARMMIND_DB_INIT_MODE", "create_all")
    dispose_engines()
    init_db()


@pytest.fixture
def approval_repo():
    return ApprovalRequestRepository()


class TestApprovalRequestRepository:
    """Approval request CRUD tests."""

    def test_create_and_get(self, approval_repo):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")

        ar = approval_repo.create(
            project_id=proj.project_id,
            title="Deploy to production",
            description="High-risk deployment",
            risk_tier="high",
            requested_capability="deploy",
        )
        assert ar.title == "Deploy to production"
        assert ar.risk_tier == "high"
        assert ar.status == "pending"
        assert ar.project_id == proj.project_id

        fetched = approval_repo.get(ar.approval_id)
        assert fetched.title == "Deploy to production"
        assert fetched.risk_tier == "high"

    def test_list_by_project(self, approval_repo):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")

        approval_repo.create(project_id=proj.project_id, title="AR 1")
        approval_repo.create(project_id=proj.project_id, title="AR 2", risk_tier="low")

        results = approval_repo.list_by_project(proj.project_id)
        assert len(results) == 2
        titles = {r.title for r in results}
        assert titles == {"AR 1", "AR 2"}

    def test_list_by_status(self, approval_repo):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")

        approval_repo.create(project_id=proj.project_id, title="Pending AR")
        ar2 = approval_repo.create(project_id=proj.project_id, title="Approved AR")
        approval_repo.update(ar2.approval_id, status="approved")

        pending = approval_repo.list_by_status("pending")
        assert len(pending) == 1
        assert pending[0].title == "Pending AR"

        approved = approval_repo.list_by_status("approved")
        assert len(approved) == 1
        assert approved[0].title == "Approved AR"

    def test_list_by_filters(self, approval_repo):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")
        proj2 = proj_repo.create(title="Other Project")

        approval_repo.create(project_id=proj.project_id, title="High Risk", risk_tier="high")
        approval_repo.create(project_id=proj.project_id, title="Medium Risk", risk_tier="medium")
        approval_repo.create(project_id=proj2.project_id, title="Other High", risk_tier="high")

        results = approval_repo.list_by_filters(project_id=proj.project_id, risk_tier="high")
        assert len(results) == 1
        assert results[0].title == "High Risk"

        results = approval_repo.list_by_filters(risk_tier="high")
        assert len(results) == 2

    def test_update(self, approval_repo):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")
        ar = approval_repo.create(project_id=proj.project_id, title="Old Title")

        updated = approval_repo.update(
            ar.approval_id,
            title="New Title",
            status="approved",
            decision_reason="Looks good",
            risk_tier="low",
        )
        assert updated.title == "New Title"
        assert updated.status == "approved"
        assert updated.decision_reason == "Looks good"
        assert updated.risk_tier == "low"

    def test_update_partial(self, approval_repo):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")
        ar = approval_repo.create(project_id=proj.project_id, title="Title", status="pending")

        updated = approval_repo.update(ar.approval_id, status="rejected")
        assert updated.status == "rejected"
        assert updated.title == "Title"

    def test_delete(self, approval_repo):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")
        ar = approval_repo.create(project_id=proj.project_id, title="To Delete")

        approval_repo.delete(ar.approval_id)

        with pytest.raises(HTTPException):
            approval_repo.get(ar.approval_id)

    def test_get_not_found(self, approval_repo):
        with pytest.raises(HTTPException):
            approval_repo.get("nonexistent")
