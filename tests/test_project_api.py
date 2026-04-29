"""Project API endpoint tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from swarmmind.api.supervisor import app
from swarmmind.db import dispose_engines, init_db
from swarmmind.repositories.conversation import ConversationRepository
from swarmmind.repositories.message import MessageRepository

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

    def test_get_project_overview(self):
        from swarmmind.repositories.approval_request import ApprovalRequestRepository
        from swarmmind.repositories.artifact import ArtifactRepository
        from swarmmind.repositories.run import RunRepository
        from swarmmind.repositories.task import TaskRepository

        # Create project
        proj_resp = client.post("/projects", json={"title": "Overview Project"})
        proj_id = proj_resp.json()["project_id"]

        task_repo = TaskRepository()
        run_repo = RunRepository()
        artifact_repo = ArtifactRepository()
        approval_repo = ApprovalRequestRepository()

        task_repo.create(project_id=proj_id, title="Task 1", status="todo")
        task_repo.create(project_id=proj_id, title="Task 2", status="blocked")
        run_repo.create(project_id=proj_id, goal="Run 1")
        artifact_repo.create(project_id=proj_id, name="Artifact 1")
        approval_repo.create(project_id=proj_id, title="Approval 1", status="pending")
        approval_repo.create(project_id=proj_id, title="Approval 2", status="approved")

        response = client.get(f"/projects/{proj_id}/overview")
        assert response.status_code == 200
        data = response.json()

        assert data["project"]["title"] == "Overview Project"
        assert data["stats"]["task_count"] == 2
        assert data["stats"]["blocked_count"] == 1
        assert data["stats"]["run_count"] == 1
        assert data["stats"]["artifact_count"] == 1
        assert data["stats"]["pending_approval_count"] == 1
        assert len(data["recent_tasks"]) == 2
        assert len(data["recent_runs"]) == 1
        assert len(data["recent_artifacts"]) == 1
        assert len(data["recent_approvals"]) == 2

    def test_get_project_overview_not_found(self):
        response = client.get("/projects/nonexistent/overview")
        assert response.status_code == 404


class TestPromoteConversation:
    """Promote to Project endpoint tests."""

    def test_promote_conversation_minimal(self):
        conv_repo = ConversationRepository()
        msg_repo = MessageRepository()
        conv = conv_repo.create("Test Chat", "pending")
        msg_repo.create(conv.id, "user", "Build a CRM")
        msg_repo.create(conv.id, "assistant", "Okay, let's plan it")

        response = client.post(f"/conversations/{conv.id}/promote")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Chat"
        assert data["source_conversation_id"] == conv.id
        assert data["goal"] is not None
        assert "project_id" in data

    def test_promote_conversation_with_overrides(self):
        conv_repo = ConversationRepository()
        msg_repo = MessageRepository()
        conv = conv_repo.create("Chat", "pending")
        msg_repo.create(conv.id, "user", "Hello")

        response = client.post(
            f"/conversations/{conv.id}/promote",
            json={"title": "Overridden Title", "goal": "Custom goal"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Overridden Title"
        assert data["goal"] == "Custom goal"

    def test_promote_conversation_links_conversation(self):
        conv_repo = ConversationRepository()
        msg_repo = MessageRepository()
        conv = conv_repo.create("Link Me", "pending")
        msg_repo.create(conv.id, "user", "Task")

        response = client.post(f"/conversations/{conv.id}/promote")
        data = response.json()

        conv_refreshed = conv_repo.get_by_id(conv.id)
        assert conv_refreshed.promoted_project_id == data["project_id"]

    def test_promote_not_found_conversation(self):
        response = client.post("/conversations/nonexistent/promote")
        assert response.status_code == 404

    def test_promote_fallback_when_no_messages(self):
        conv_repo = ConversationRepository()
        conv = conv_repo.create("Empty Chat", "pending")

        response = client.post(f"/conversations/{conv.id}/promote")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Empty Chat"
        assert data["source_conversation_id"] == conv.id
