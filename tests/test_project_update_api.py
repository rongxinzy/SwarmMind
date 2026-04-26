"""Project PATCH endpoint tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from swarmmind.api.supervisor import app
from swarmmind.db import dispose_engines, init_db
from swarmmind.repositories.project import ProjectRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "project_update_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SWARMMIND_DB_INIT_MODE", "create_all")
    dispose_engines()
    init_db()


class TestUpdateProject:
    """Project PATCH API tests."""

    def test_update_title(self):
        repo = ProjectRepository()
        proj = repo.create(title="Old Title", goal="Do work")

        response = client.patch(f"/projects/{proj.project_id}", json={"title": "New Title"})
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"
        assert data["goal"] == "Do work"  # unchanged

    def test_update_status(self):
        repo = ProjectRepository()
        proj = repo.create(title="Project", goal="Work")

        response = client.patch(f"/projects/{proj.project_id}", json={"status": "archived"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "archived"

    def test_update_multiple_fields(self):
        repo = ProjectRepository()
        proj = repo.create(title="Project", goal="Old Goal")

        response = client.patch(
            f"/projects/{proj.project_id}",
            json={"title": "Updated", "goal": "New Goal", "next_step": "Review"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated"
        assert data["goal"] == "New Goal"
        assert data["next_step"] == "Review"

    def test_update_no_fields(self):
        repo = ProjectRepository()
        proj = repo.create(title="Project", goal="Work")

        response = client.patch(f"/projects/{proj.project_id}", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Project"
        assert data["goal"] == "Work"

    def test_update_not_found(self):
        response = client.patch("/projects/nonexistent", json={"title": "X"})
        assert response.status_code == 404
