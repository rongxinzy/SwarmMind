"""Run API endpoint tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from swarmmind.api.supervisor import app
from swarmmind.db import dispose_engines, init_db
from swarmmind.repositories.conversation import ConversationRepository
from swarmmind.repositories.project import ProjectRepository
from swarmmind.repositories.run import RunRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "run_api_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SWARMMIND_DB_INIT_MODE", "create_all")
    dispose_engines()
    init_db()


class TestRunEndpoints:
    """Run REST API tests."""

    def test_list_project_runs_empty(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Project")

        response = client.get(f"/projects/{proj.project_id}/runs")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_project_runs_with_items(self):
        conv_repo = ConversationRepository()
        proj_repo = ProjectRepository()
        run_repo = RunRepository()
        conv = conv_repo.create("Chat", "pending")
        proj = proj_repo.create(title="Project")
        run_repo.create(conversation_id=conv.id, project_id=proj.project_id, goal="Run 1")
        run_repo.create(conversation_id=conv.id, project_id=proj.project_id, goal="Run 2")

        response = client.get(f"/projects/{proj.project_id}/runs")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        goals = {r["goal"] for r in data["items"]}
        assert goals == {"Run 1", "Run 2"}

    def test_list_project_runs_project_not_found(self):
        response = client.get("/projects/nonexistent/runs")
        assert response.status_code == 404

    def test_get_run(self):
        conv_repo = ConversationRepository()
        run_repo = RunRepository()
        conv = conv_repo.create("Chat", "pending")
        run = run_repo.create(conversation_id=conv.id, goal="Do work")

        response = client.get(f"/runs/{run.run_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run.run_id
        assert data["goal"] == "Do work"
        assert data["status"] == "running"

    def test_get_run_not_found(self):
        response = client.get("/runs/nonexistent")
        assert response.status_code == 404

    def test_create_run(self):
        conv_repo = ConversationRepository()
        conv = conv_repo.create("Chat", "pending")

        response = client.post("/runs", json={"conversation_id": conv.id, "goal": "New run"})
        assert response.status_code == 200
        data = response.json()
        assert data["goal"] == "New run"
        assert data["conversation_id"] == conv.id
        assert data["status"] == "running"
        assert "run_id" in data

    def test_create_run_conversation_not_found(self):
        response = client.post("/runs", json={"conversation_id": "nonexistent", "goal": "X"})
        assert response.status_code == 404
