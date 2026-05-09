"""Run lifecycle service tests.

Covers: start→finish, start→fail, start→pause→resume, and ChatSession no-op behavior.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from swarmmind.db import dispose_engines, init_db
from swarmmind.repositories.conversation import ConversationRepository
from swarmmind.repositories.project import ProjectRepository
from swarmmind.repositories.run import RunRepository
from swarmmind.services.run_context import RiskPolicy, RunContext
from swarmmind.services.run_lifecycle import RunLifecycleService


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "run_lifecycle_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    dispose_engines()
    init_db()


@pytest.fixture
def run_repo():
    return RunRepository()


@pytest.fixture
def lifecycle(run_repo):
    return RunLifecycleService(run_repo=run_repo)


@pytest.fixture
def project():
    return ProjectRepository().create(title="Test Project")


@pytest.fixture
def conversation():
    return ConversationRepository().create("Test Chat", "pending")


class TestRunContext:
    def test_for_chat_session_has_no_project(self, conversation):
        ctx = RunContext.for_chat_session(conversation.id)
        assert ctx.project_id is None
        assert ctx.conversation_id == conversation.id
        assert ctx.risk_policy == RiskPolicy.PERMISSIVE
        assert ctx.approver_role is None
        assert ctx.run_id  # non-empty

    def test_for_project_sets_fields(self, project, conversation):
        ctx = RunContext.for_project(project.project_id, conversation.id)
        assert ctx.project_id == project.project_id
        assert ctx.conversation_id == conversation.id
        assert ctx.risk_policy == RiskPolicy.MODERATE
        assert ctx.run_id

    def test_for_project_custom_policy(self, project, conversation):
        ctx = RunContext.for_project(project.project_id, conversation.id, risk_policy=RiskPolicy.STRICT)
        assert ctx.risk_policy == RiskPolicy.STRICT

    def test_run_ids_are_unique(self, conversation):
        ctx1 = RunContext.for_chat_session(conversation.id)
        ctx2 = RunContext.for_chat_session(conversation.id)
        assert ctx1.run_id != ctx2.run_id


class TestRunLifecycleServiceNoOp:
    """ChatSession-only runs (project_id=None) must produce zero DB rows."""

    def test_start_noop_returns_none(self, lifecycle, conversation):
        ctx = RunContext.for_chat_session(conversation.id)
        result = lifecycle.start(ctx)
        assert result is None

    def test_finish_noop(self, lifecycle, conversation, run_repo):
        ctx = RunContext.for_chat_session(conversation.id)
        lifecycle.start(ctx)
        lifecycle.finish(ctx, summary="done")
        # No RunDB row should exist
        with pytest.raises(HTTPException):
            run_repo.get_by_id(ctx.run_id)

    def test_fail_noop(self, lifecycle, conversation, run_repo):
        ctx = RunContext.for_chat_session(conversation.id)
        lifecycle.start(ctx)
        lifecycle.fail(ctx, "RUNTIME_ERROR", "something broke")
        with pytest.raises(HTTPException):
            run_repo.get_by_id(ctx.run_id)

    def test_pause_and_resume_noop(self, lifecycle, conversation, run_repo):
        ctx = RunContext.for_chat_session(conversation.id)
        lifecycle.start(ctx)
        lifecycle.pause_for_approval(ctx, "approval-123")
        lifecycle.resume(ctx)
        with pytest.raises(HTTPException):
            run_repo.get_by_id(ctx.run_id)


class TestRunLifecycleServiceProjectScoped:
    """Project-scoped runs must create and transition RunDB rows."""

    def test_start_creates_run_row(self, lifecycle, project, conversation, run_repo):
        ctx = RunContext.for_project(project.project_id, conversation.id)
        run = lifecycle.start(ctx)
        assert run is not None
        assert run.run_id == ctx.run_id
        assert run.project_id == project.project_id
        assert run.conversation_id == conversation.id
        assert run.status == "running"

    def test_start_finish_completes_run(self, lifecycle, project, conversation, run_repo):
        ctx = RunContext.for_project(project.project_id, conversation.id)
        lifecycle.start(ctx)
        lifecycle.finish(ctx, summary="All done")

        run = run_repo.get_by_id(ctx.run_id)
        assert run.status == "completed"
        assert run.summary == "All done"
        assert run.completed_at is not None

    def test_start_finish_no_summary(self, lifecycle, project, conversation, run_repo):
        ctx = RunContext.for_project(project.project_id, conversation.id)
        lifecycle.start(ctx)
        lifecycle.finish(ctx)

        run = run_repo.get_by_id(ctx.run_id)
        assert run.status == "completed"

    def test_start_fail_marks_failed(self, lifecycle, project, conversation, run_repo):
        ctx = RunContext.for_project(project.project_id, conversation.id)
        lifecycle.start(ctx)
        lifecycle.fail(ctx, "TIMEOUT", "took too long")

        run = run_repo.get_by_id(ctx.run_id)
        assert run.status == "failed"
        assert "TIMEOUT" in run.summary
        assert "took too long" in run.summary
        assert run.completed_at is not None

    def test_start_pause_resume_transitions(self, lifecycle, project, conversation, run_repo):
        ctx = RunContext.for_project(project.project_id, conversation.id)
        lifecycle.start(ctx)

        lifecycle.pause_for_approval(ctx, "approval-abc")
        run = run_repo.get_by_id(ctx.run_id)
        assert run.status == "waiting_approval"

        lifecycle.resume(ctx)
        run = run_repo.get_by_id(ctx.run_id)
        assert run.status == "running"

    def test_start_pause_fail(self, lifecycle, project, conversation, run_repo):
        ctx = RunContext.for_project(project.project_id, conversation.id)
        lifecycle.start(ctx)
        lifecycle.pause_for_approval(ctx, "approval-xyz")
        lifecycle.fail(ctx, "approval_rejected", "user rejected")

        run = run_repo.get_by_id(ctx.run_id)
        assert run.status == "failed"

    def test_run_anchored_on_project(self, lifecycle, project, conversation, run_repo):
        ctx = RunContext.for_project(project.project_id, conversation.id)
        lifecycle.start(ctx)
        lifecycle.finish(ctx, "summary")

        runs = run_repo.list_by_project(project.project_id)
        assert len(runs) == 1
        assert runs[0].run_id == ctx.run_id


class TestRunRepositoryLifecycleHelpers:
    """Unit tests for the new RunRepository lifecycle helper methods."""

    def test_mark_completed(self, run_repo, project, conversation):
        run = run_repo.create(
            project_id=project.project_id,
            conversation_id=conversation.id,
            status="running",
        )
        run_repo.mark_completed(run.run_id, summary="finished")
        fetched = run_repo.get_by_id(run.run_id)
        assert fetched.status == "completed"
        assert fetched.summary == "finished"
        assert fetched.completed_at is not None

    def test_mark_failed(self, run_repo, project, conversation):
        run = run_repo.create(
            project_id=project.project_id,
            conversation_id=conversation.id,
        )
        run_repo.mark_failed(run.run_id, "RUNTIME_ERROR", "boom")
        fetched = run_repo.get_by_id(run.run_id)
        assert fetched.status == "failed"
        assert "RUNTIME_ERROR" in fetched.summary
        assert fetched.completed_at is not None

    def test_mark_waiting_approval(self, run_repo, project, conversation):
        run = run_repo.create(project_id=project.project_id)
        run_repo.mark_waiting_approval(run.run_id, "approval-999")
        fetched = run_repo.get_by_id(run.run_id)
        assert fetched.status == "waiting_approval"

    def test_mark_running(self, run_repo, project):
        run = run_repo.create(project_id=project.project_id, status="waiting_approval")
        run_repo.mark_running(run.run_id)
        fetched = run_repo.get_by_id(run.run_id)
        assert fetched.status == "running"

    def test_create_with_explicit_run_id(self, run_repo, project):
        explicit_id = "my-deterministic-run-id"
        run = run_repo.create(run_id=explicit_id, project_id=project.project_id)
        assert run.run_id == explicit_id
        fetched = run_repo.get_by_id(explicit_id)
        assert fetched.run_id == explicit_id

    def test_mark_completed_not_found_raises(self, run_repo):
        with pytest.raises(HTTPException):
            run_repo.mark_completed("nonexistent-run-id")

    def test_mark_failed_not_found_raises(self, run_repo):
        with pytest.raises(HTTPException):
            run_repo.mark_failed("nonexistent-run-id", "ERR", "msg")
