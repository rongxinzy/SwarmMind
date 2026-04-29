"""Run repository tests."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from swarmmind.db import dispose_engines, init_db
from swarmmind.repositories.conversation import ConversationRepository
from swarmmind.repositories.project import ProjectRepository
from swarmmind.repositories.run import RunRepository


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "run_repo_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SWARMMIND_DB_INIT_MODE", "create_all")
    dispose_engines()
    init_db()


@pytest.fixture
def run_repo():
    return RunRepository()


class TestRunRepository:
    """Run CRUD tests."""

    def test_create_and_get(self, run_repo):
        conv_repo = ConversationRepository()
        conv = conv_repo.create("Chat", "pending")

        run = run_repo.create(conversation_id=conv.id, goal="Build a CRM")
        assert run.goal == "Build a CRM"
        assert run.status == "running"
        assert run.conversation_id == conv.id
        assert run.project_id is None

        fetched = run_repo.get_by_id(run.run_id)
        assert fetched.goal == "Build a CRM"

    def test_create_with_project(self, run_repo):
        conv_repo = ConversationRepository()
        proj_repo = ProjectRepository()
        conv = conv_repo.create("Chat", "pending")
        proj = proj_repo.create(title="CRM Project")

        run = run_repo.create(conversation_id=conv.id, project_id=proj.project_id, goal="Plan it")
        assert run.project_id == proj.project_id

    def test_list_by_project(self, run_repo):
        conv_repo = ConversationRepository()
        proj_repo = ProjectRepository()
        conv = conv_repo.create("Chat", "pending")
        proj = proj_repo.create(title="P")

        run_repo.create(conversation_id=conv.id, project_id=proj.project_id, goal="A")
        run_repo.create(conversation_id=conv.id, project_id=proj.project_id, goal="B")

        results = run_repo.list_by_project(proj.project_id)
        assert len(results) == 2
        goals = {r.goal for r in results}
        assert goals == {"A", "B"}

    def test_list_by_conversation(self, run_repo):
        conv_repo = ConversationRepository()
        conv = conv_repo.create("Chat", "pending")

        run_repo.create(conversation_id=conv.id, goal="X")
        run_repo.create(conversation_id=conv.id, goal="Y")

        results = run_repo.list_by_conversation(conv.id)
        assert len(results) == 2

    def test_update_status(self, run_repo):
        conv_repo = ConversationRepository()
        conv = conv_repo.create("Chat", "pending")
        run = run_repo.create(conversation_id=conv.id, goal="Work")

        run_repo.update_status(run.run_id, "completed", summary="Done")

        fetched = run_repo.get_by_id(run.run_id)
        assert fetched.status == "completed"
        assert fetched.summary == "Done"
        assert fetched.completed_at is not None

    def test_link_project(self, run_repo):
        conv_repo = ConversationRepository()
        proj_repo = ProjectRepository()
        conv = conv_repo.create("Chat", "pending")
        proj = proj_repo.create(title="P")
        run = run_repo.create(conversation_id=conv.id, goal="Work")

        run_repo.link_project(run.run_id, proj.project_id)

        fetched = run_repo.get_by_id(run.run_id)
        assert fetched.project_id == proj.project_id

    def test_create_with_project_only(self, run_repo):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="CRM Project")

        run = run_repo.create(project_id=proj.project_id, goal="Plan it")
        assert run.project_id == proj.project_id
        assert run.conversation_id is None
        assert run.goal == "Plan it"

    def test_get_not_found(self, run_repo):
        with pytest.raises(HTTPException):
            run_repo.get_by_id("nonexistent")
