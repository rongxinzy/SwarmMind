"""Project API endpoint tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from swarmmind.api.supervisor import app
from swarmmind.db import dispose_engines, init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    dispose_engines()
    init_db()


class TestProjectEndpoints:
    """Project REST API tests."""

    def test_list_projects_empty(self):
        response = client.get("/projects")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_create_project(self):
        response = client.post("/projects", json={"title": "New Project", "goal": "Do work"})
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Project"
        assert data["goal"] == "Do work"
        assert data["status"] == "active"
        assert "project_id" in data

    def test_get_project(self):
        created = client.post("/projects", json={"title": "Fetch Me"}).json()
        response = client.get(f"/projects/{created['project_id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Fetch Me"

    def test_get_project_not_found(self):
        response = client.get("/projects/nonexistent")
        assert response.status_code == 404

    def test_list_projects_after_create(self):
        client.post("/projects", json={"title": "A"})
        client.post("/projects", json={"title": "B"})
        response = client.get("/projects")
        data = response.json()
        assert data["total"] >= 2
        titles = [p["title"] for p in data["items"]]
        assert "A" in titles
        assert "B" in titles

    def test_list_projects_supports_limit_and_offset(self):
        client.post("/projects", json={"title": "A"})
        client.post("/projects", json={"title": "B"})
        client.post("/projects", json={"title": "C"})

        response = client.get("/projects", params={"limit": 1, "offset": 1})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 1

    def test_create_project_with_phase_and_risk_level(self):
        response = client.post(
            "/projects",
            json={
                "title": "Phased Project",
                "phase": "需求澄清",
                "risk_level": "high",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Phased Project"
        assert data["phase"] == "需求澄清"
        assert data["risk_level"] == "high"

    def test_update_project(self):
        created = client.post("/projects", json={"title": "Old Title"}).json()
        project_id = created["project_id"]

        response = client.patch(
            f"/projects/{project_id}",
            json={"title": "New Title", "goal": "Updated goal"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"
        assert data["goal"] == "Updated goal"

    def test_delete_project(self):
        created = client.post("/projects", json={"title": "Delete Me"}).json()
        project_id = created["project_id"]

        response = client.delete(f"/projects/{project_id}")
        assert response.status_code == 200
        assert response.json()["project_id"] == project_id

        response = client.get(f"/projects/{project_id}")
        assert response.status_code == 404
