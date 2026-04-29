"""Task API endpoint tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from swarmmind.api.supervisor import app
from swarmmind.db import dispose_engines, init_db
from swarmmind.repositories.project import ProjectRepository
from swarmmind.repositories.task import TaskRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "task_api_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    dispose_engines()
    init_db()


class TestTaskEndpoints:
    """Task REST API tests."""

    def test_list_project_tasks_empty(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Project")

        response = client.get(f"/projects/{proj.project_id}/tasks")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_project_tasks_with_items(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Project")
        task_repo = TaskRepository()
        task_repo.create(project_id=proj.project_id, title="Task 1")
        task_repo.create(project_id=proj.project_id, title="Task 2", status="in_progress")

        response = client.get(f"/projects/{proj.project_id}/tasks")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        titles = {t["title"] for t in data["items"]}
        assert titles == {"Task 1", "Task 2"}

    def test_list_project_tasks_project_not_found(self):
        response = client.get("/projects/nonexistent/tasks")
        assert response.status_code == 404

    def test_create_task(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Project")

        response = client.post(
            f"/projects/{proj.project_id}/tasks",
            json={"title": "New Task", "description": "Do work", "priority": "high"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Task"
        assert data["description"] == "Do work"
        assert data["status"] == "todo"
        assert data["priority"] == "high"
        assert data["project_id"] == proj.project_id
        assert "task_id" in data

    def test_create_task_project_not_found(self):
        response = client.post(
            "/projects/nonexistent/tasks",
            json={"title": "Task"},
        )
        assert response.status_code == 404

    def test_get_task(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Project")
        task_repo = TaskRepository()
        task = task_repo.create(project_id=proj.project_id, title="Fetch Me")

        response = client.get(f"/projects/{proj.project_id}/tasks/{task.task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Fetch Me"
        assert data["task_id"] == task.task_id

    def test_get_task_not_found(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Project")

        response = client.get(f"/projects/{proj.project_id}/tasks/nonexistent")
        assert response.status_code == 404

    def test_get_task_wrong_project(self):
        proj_repo = ProjectRepository()
        proj1 = proj_repo.create(title="Project 1")
        proj2 = proj_repo.create(title="Project 2")
        task_repo = TaskRepository()
        task = task_repo.create(project_id=proj1.project_id, title="Task")

        response = client.get(f"/projects/{proj2.project_id}/tasks/{task.task_id}")
        assert response.status_code == 404

    def test_update_task(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Project")
        task_repo = TaskRepository()
        task = task_repo.create(project_id=proj.project_id, title="Old Title")

        response = client.patch(
            f"/projects/{proj.project_id}/tasks/{task.task_id}",
            json={"title": "New Title", "status": "in_progress"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"
        assert data["status"] == "in_progress"

    def test_update_task_not_found(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Project")

        response = client.patch(
            f"/projects/{proj.project_id}/tasks/nonexistent",
            json={"title": "New Title"},
        )
        assert response.status_code == 404

    def test_delete_task(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Project")
        task_repo = TaskRepository()
        task = task_repo.create(project_id=proj.project_id, title="To Delete")

        response = client.delete(f"/projects/{proj.project_id}/tasks/{task.task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["task_id"] == task.task_id

        response = client.get(f"/projects/{proj.project_id}/tasks/{task.task_id}")
        assert response.status_code == 404

    def test_delete_task_not_found(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Project")

        response = client.delete(f"/projects/{proj.project_id}/tasks/nonexistent")
        assert response.status_code == 404
