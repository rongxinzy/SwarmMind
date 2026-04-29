"""Artifact repository tests."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from swarmmind.db import dispose_engines, init_db
from swarmmind.repositories.artifact import ArtifactRepository
from swarmmind.repositories.conversation import ConversationRepository
from swarmmind.repositories.project import ProjectRepository
from swarmmind.repositories.run import RunRepository
from swarmmind.repositories.task import TaskRepository


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "artifact_repo_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SWARMMIND_DB_INIT_MODE", "create_all")
    dispose_engines()
    init_db()


@pytest.fixture
def artifact_repo():
    return ArtifactRepository()


class TestArtifactRepository:
    """Artifact CRUD tests."""

    def test_create_and_get(self, artifact_repo):
        conv_repo = ConversationRepository()
        conv = conv_repo.create("Chat", "pending")

        art = artifact_repo.create(
            conversation_id=conv.id,
            message_id=None,
            name="report.md",
            artifact_type="write_file",
        )
        assert art.name == "report.md"
        assert art.artifact_type == "write_file"
        assert art.conversation_id == conv.id

        fetched = artifact_repo.get_by_id(art.artifact_id)
        assert fetched.name == "report.md"

    def test_list_by_conversation(self, artifact_repo):
        conv_repo = ConversationRepository()
        conv = conv_repo.create("Chat", "pending")

        artifact_repo.create(conv.id, None, "a.md", "write_file")
        artifact_repo.create(conv.id, None, "b.md", "edit_file")

        results = artifact_repo.list_by_conversation(conv.id)
        assert len(results) == 2
        names = {r.name for r in results}
        assert names == {"a.md", "b.md"}

    def test_list_by_conversation_empty(self, artifact_repo):
        conv_repo = ConversationRepository()
        conv = conv_repo.create("Chat", "pending")

        results = artifact_repo.list_by_conversation(conv.id)
        assert results == []

    def test_delete(self, artifact_repo):
        conv_repo = ConversationRepository()
        conv = conv_repo.create("Chat", "pending")
        art = artifact_repo.create(conv.id, None, "x.md", "write_file")

        artifact_repo.delete(art.artifact_id)

        with pytest.raises(HTTPException):
            artifact_repo.get_by_id(art.artifact_id)

    def test_get_not_found(self, artifact_repo):
        with pytest.raises(HTTPException):
            artifact_repo.get_by_id("nonexistent")

    def test_create_with_trace_fields(self, artifact_repo):
        conv_repo = ConversationRepository()
        conv = conv_repo.create("Chat", "pending")

        run_repo = RunRepository()
        run = run_repo.create(conversation_id=conv.id)

        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")

        task_repo = TaskRepository()
        task = task_repo.create(project_id=proj.project_id, title="Test Task")

        art = artifact_repo.create(
            conversation_id=conv.id,
            message_id=None,
            name="report.md",
            artifact_type="write_file",
            run_id=run.run_id,
            task_id=task.task_id,
            author_role="架构专家",
        )
        assert art.run_id == run.run_id
        assert art.task_id == task.task_id
        assert art.author_role == "架构专家"

        fetched = artifact_repo.get_by_id(art.artifact_id)
        assert fetched.run_id == run.run_id
        assert fetched.task_id == task.task_id
        assert fetched.author_role == "架构专家"
