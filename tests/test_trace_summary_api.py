"""Tests for GET /conversations/{id}/messages/{msg_id}/trace endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from swarmmind.api import supervisor
from swarmmind.api.supervisor import app
from swarmmind.db import dispose_engines, init_db
from swarmmind.models import TraceSummaryResponse
from swarmmind.repositories.conversation import ConversationRepository
from swarmmind.repositories.message import MessageRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "trace_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SWARMMIND_DB_INIT_MODE", "create_all")
    dispose_engines()
    init_db()


class TestTraceSummaryEndpoint:
    """Trace summary REST API tests."""

    def test_get_trace_summary_success(self, monkeypatch):
        conv_repo = ConversationRepository()
        msg_repo = MessageRepository()
        conv = conv_repo.create("Chat", "pending")
        msg = msg_repo.create(conv.id, "assistant", "Result here", run_id="run-1")

        mock_svc = MagicMock()
        mock_svc.get_summary.return_value = TraceSummaryResponse(
            steps_count=3,
            subagent_calls_count=1,
            artifacts_count=1,
            blocked_points=[],
            summary="用户输入 1 轮，子代理协作 1 次，生成产物 1 个",
        )
        monkeypatch.setattr(supervisor, "message_trace_service", mock_svc)

        response = client.get(f"/conversations/{conv.id}/messages/{msg.id}/trace")
        assert response.status_code == 200
        data = response.json()
        assert data["steps_count"] == 3
        assert data["subagent_calls_count"] == 1
        assert data["artifacts_count"] == 1
        assert data["summary"] == "用户输入 1 轮，子代理协作 1 次，生成产物 1 个"
        mock_svc.get_summary.assert_called_once_with(conv.id, msg.id)

    def test_get_trace_summary_conversation_not_found(self):
        response = client.get("/conversations/nonexistent/messages/msg-1/trace")
        assert response.status_code == 404

    def test_get_trace_summary_message_not_found(self):
        conv_repo = ConversationRepository()
        conv = conv_repo.create("Chat", "pending")

        response = client.get(f"/conversations/{conv.id}/messages/nonexistent/trace")
        assert response.status_code == 404

    def test_get_trace_summary_message_wrong_conversation(self):
        conv_repo = ConversationRepository()
        msg_repo = MessageRepository()
        conv1 = conv_repo.create("Chat 1", "pending")
        conv2 = conv_repo.create("Chat 2", "pending")
        msg = msg_repo.create(conv2.id, "assistant", "Result")

        response = client.get(f"/conversations/{conv1.id}/messages/{msg.id}/trace")
        assert response.status_code == 404

    def test_get_trace_summary_service_failure_degrades(self, monkeypatch):
        conv_repo = ConversationRepository()
        msg_repo = MessageRepository()
        conv = conv_repo.create("Chat", "pending")
        msg = msg_repo.create(conv.id, "assistant", "Result here", run_id="run-1")

        mock_svc = MagicMock()
        mock_svc.get_summary.side_effect = RuntimeError("checkpoint corrupted")
        monkeypatch.setattr(supervisor, "message_trace_service", mock_svc)

        response = client.get(f"/conversations/{conv.id}/messages/{msg.id}/trace")
        assert response.status_code == 200
        data = response.json()
        # Degraded fallback based on run_id presence
        assert data["steps_count"] == 1
        assert data["summary"] == "执行完成"

    def test_get_trace_summary_no_run_id(self, monkeypatch):
        conv_repo = ConversationRepository()
        msg_repo = MessageRepository()
        conv = conv_repo.create("Chat", "pending")
        msg = msg_repo.create(conv.id, "assistant", "Quick reply", run_id=None)

        mock_svc = MagicMock()
        mock_svc.get_summary.return_value = TraceSummaryResponse(
            steps_count=0,
            subagent_calls_count=0,
            artifacts_count=0,
            blocked_points=[],
            summary="直接回复",
        )
        monkeypatch.setattr(supervisor, "message_trace_service", mock_svc)

        response = client.get(f"/conversations/{conv.id}/messages/{msg.id}/trace")
        assert response.status_code == 200
        data = response.json()
        assert data["steps_count"] == 0
        assert data["summary"] == "直接回复"
