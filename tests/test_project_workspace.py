"""Tests for project workspace endpoints (sessions, memory, files)."""

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
    monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    dispose_engines()
    init_db()


class TestProjectWorkspaceEndpoints:
    """Tests for /projects/{id}/* workspace endpoints."""

    def test_list_project_conversations_empty(self):
        proj = client.post("/projects", json={"title": "P1"}).json()
        response = client.get(f"/projects/{proj['project_id']}/conversations")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_create_project_conversation(self):
        proj = client.post("/projects", json={"title": "P1"}).json()
        response = client.post(f"/projects/{proj['project_id']}/conversations")
        assert response.status_code == 200
        data = response.json()
        assert data["session_type"] == "task"
        assert data["project_id"] == proj["project_id"]

    def test_list_project_conversations_only_project_sessions(self):
        proj = client.post("/projects", json={"title": "P1"}).json()
        proj2 = client.post("/projects", json={"title": "P2"}).json()

        conv1 = client.post(f"/projects/{proj['project_id']}/conversations").json()
        client.post(f"/projects/{proj2['project_id']}/conversations")

        response = client.get(f"/projects/{proj['project_id']}/conversations")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == conv1["id"]

    def test_project_memory_crud(self):
        proj = client.post("/projects", json={"title": "P1"}).json()

        response = client.get(f"/projects/{proj['project_id']}/memory")
        assert response.status_code == 200
        assert response.json()["items"] == []

        response = client.put(
            f"/projects/{proj['project_id']}/memory/goal",
            json={"value": "build chat app"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "goal"
        assert data["value"] == "build chat app"

        response = client.put(
            f"/projects/{proj['project_id']}/memory/goal",
            json={"value": "build agent chat app"},
        )
        assert response.status_code == 200
        assert response.json()["value"] == "build agent chat app"

        response = client.get(f"/projects/{proj['project_id']}/memory")
        assert response.status_code == 200
        assert len(response.json()["items"]) == 1

        response = client.delete(f"/projects/{proj['project_id']}/memory/goal")
        assert response.status_code == 200

        response = client.get(f"/projects/{proj['project_id']}/memory")
        assert response.status_code == 200
        assert response.json()["items"] == []

    def test_project_files_list_empty(self):
        proj = client.post("/projects", json={"title": "P1"}).json()
        response = client.get(f"/projects/{proj['project_id']}/files")
        assert response.status_code == 200
        assert response.json()["files"] == []

    def test_project_workspace_not_found(self):
        response = client.get("/projects/nonexistent/conversations")
        assert response.status_code == 404

        response = client.post("/projects/nonexistent/conversations")
        assert response.status_code == 404

        response = client.get("/projects/nonexistent/memory")
        assert response.status_code == 404

        response = client.put("/projects/nonexistent/memory/k", json={"value": "v"})
        assert response.status_code == 404
