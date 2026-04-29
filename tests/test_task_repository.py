"""Task repository tests."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from swarmmind.db import dispose_engines, init_db
from swarmmind.repositories.project import ProjectRepository
from swarmmind.repositories.task import TaskRepository


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "task_repo_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    dispose_engines()
    init_db()


@pytest.fixture
def task_repo():
    return TaskRepository()


class TestTaskRepository:
    """Task CRUD tests."""

    def test_create_and_get(self, task_repo):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")

        task = task_repo.create(
            project_id=proj.project_id,
            title="Build feature",
            description="Implement the thing",
            status="todo",
            priority="high",
        )
        assert task.title == "Build feature"
        assert task.status == "todo"
        assert task.priority == "high"
        assert task.project_id == proj.project_id

        fetched = task_repo.get_by_id(task.task_id)
        assert fetched.title == "Build feature"

    def test_list_by_project(self, task_repo):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")

        task_repo.create(project_id=proj.project_id, title="Task A")
        task_repo.create(project_id=proj.project_id, title="Task B", status="in_progress")

        results = task_repo.list_by_project(proj.project_id)
        assert len(results) == 2
        titles = {r.title for r in results}
        assert titles == {"Task A", "Task B"}

    def test_list_by_project_empty(self, task_repo):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")

        results = task_repo.list_by_project(proj.project_id)
        assert results == []

    def test_update(self, task_repo):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")
        task = task_repo.create(project_id=proj.project_id, title="Old Title")

        updated = task_repo.update(
            task.task_id,
            title="New Title",
            status="in_progress",
            assignee_role="产品专家",
        )
        assert updated.title == "New Title"
        assert updated.status == "in_progress"
        assert updated.assignee_role == "产品专家"

    def test_update_partial(self, task_repo):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")
        task = task_repo.create(project_id=proj.project_id, title="Task", status="todo")

        updated = task_repo.update(task.task_id, status="done")
        assert updated.status == "done"
        assert updated.title == "Task"

    def test_delete(self, task_repo):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")
        task = task_repo.create(project_id=proj.project_id, title="To Delete")

        task_repo.delete(task.task_id)

        with pytest.raises(HTTPException):
            task_repo.get_by_id(task.task_id)

    def test_get_not_found(self, task_repo):
        with pytest.raises(HTTPException):
            task_repo.get_by_id("nonexistent")
