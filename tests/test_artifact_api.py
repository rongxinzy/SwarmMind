"""Artifact API endpoint tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from swarmmind.api import supervisor
from swarmmind.api.supervisor import app
from swarmmind.db import dispose_engines, init_db
from swarmmind.repositories.artifact import ArtifactRepository
from swarmmind.repositories.conversation import ConversationRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "artifact_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SWARMMIND_DB_INIT_MODE", "create_all")
    dispose_engines()
    init_db()


class TestArtifactEndpoints:
    """Artifact REST API tests."""

    def test_list_artifacts_empty(self):
        conv_repo = ConversationRepository()
        conv = conv_repo.create("Chat", "pending")

        response = client.get(f"/conversations/{conv.id}/artifacts")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_artifacts_with_items(self):
        conv_repo = ConversationRepository()
        art_repo = ArtifactRepository()
        conv = conv_repo.create("Chat", "pending")
        art_repo.create(conv.id, None, "report.md", "write_file")
        art_repo.create(conv.id, None, "plan.md", "present_files")

        response = client.get(f"/conversations/{conv.id}/artifacts")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        names = {a["name"] for a in data["items"]}
        assert names == {"report.md", "plan.md"}

    def test_list_artifacts_conversation_not_found(self):
        response = client.get("/conversations/nonexistent/artifacts")
        assert response.status_code == 404

    def test_extract_artifacts_from_trace(self, monkeypatch):
        conv_repo = ConversationRepository()
        conv = conv_repo.create("Chat", "pending")

        mock_svc = MagicMock()
        mock_svc.extract_artifacts.return_value = [
            {"artifact_id": "art-1", "name": "output.md", "artifact_type": "write_file"},
        ]
        monkeypatch.setattr(supervisor, "message_trace_service", mock_svc)

        response = client.post(f"/conversations/{conv.id}/extract-artifacts")
        assert response.status_code == 200
        data = response.json()
        assert data["extracted"] == 1
        assert data["artifacts"][0]["name"] == "output.md"
        mock_svc.extract_artifacts.assert_called_once_with(conv.id, project_id=None)

    def test_extract_artifacts_conversation_not_found(self):
        response = client.post("/conversations/nonexistent/extract-artifacts")
        assert response.status_code == 404

    def test_extract_artifacts_empty(self, monkeypatch):
        conv_repo = ConversationRepository()
        conv = conv_repo.create("Chat", "pending")

        mock_svc = MagicMock()
        mock_svc.extract_artifacts.return_value = []
        monkeypatch.setattr(supervisor, "message_trace_service", mock_svc)

        response = client.post(f"/conversations/{conv.id}/extract-artifacts")
        assert response.status_code == 200
        data = response.json()
        assert data["extracted"] == 0
