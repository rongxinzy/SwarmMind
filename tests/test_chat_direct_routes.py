"""Tests for direct Chat mode routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from swarmmind.api.supervisor import app
from swarmmind.db import dispose_engines, init_db
from swarmmind.runtime.catalog import sync_env_runtime_model

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("LLM_MODEL", "qwen3.5-plus")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    dispose_engines()
    init_db()
    sync_env_runtime_model()


class TestChatDirectRoutes:
    """Tests for /chat/* endpoints."""

    def test_list_chat_models_returns_models_and_credentials(self):
        response = client.get("/chat/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "default_model" in data
        assert len(data["models"]) >= 1
        model = data["models"][0]
        assert "id" in model
        assert "base_url" in model
        assert "api_key" in model
        assert model["api_key"].startswith("sk-swarmmind-")

    def test_create_chat_conversation(self):
        response = client.post("/chat/conversations")
        assert response.status_code == 200
        data = response.json()
        assert data["session_type"] == "chat"
        assert data["title"] == "New Chat"

    def test_list_chat_conversations_only_chat(self):
        # Create a chat conversation
        chat_resp = client.post("/chat/conversations")
        assert chat_resp.status_code == 200
        chat_id = chat_resp.json()["id"]

        # Create a task conversation via the generic endpoint
        task_resp = client.post("/conversations", json={"title": "Task conv", "session_type": "task"})
        assert task_resp.status_code == 200
        task_id = task_resp.json()["id"]

        response = client.get("/chat/conversations")
        assert response.status_code == 200
        data = response.json()
        ids = {c["id"] for c in data["items"]}
        assert chat_id in ids
        assert task_id not in ids
        assert all(c["session_type"] == "chat" for c in data["items"])

    def test_persist_and_list_chat_messages(self):
        conv_resp = client.post("/chat/conversations")
        assert conv_resp.status_code == 200
        conv_id = conv_resp.json()["id"]

        response = client.post(
            f"/chat/conversations/{conv_id}/messages",
            json={
                "messages": [
                    {"role": "user", "content": "hello"},
                    {"role": "assistant", "content": "hi there"},
                ]
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"

        response = client.get(f"/chat/conversations/{conv_id}/messages")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2

    def test_persist_chat_title_from_first_user_message(self):
        conv_resp = client.post("/chat/conversations")
        conv_id = conv_resp.json()["id"]

        response = client.post(
            f"/chat/conversations/{conv_id}/messages",
            json={
                "messages": [
                    {"role": "user", "content": "tell me about python"},
                    {"role": "assistant", "content": "Python is a programming language."},
                ]
            },
        )
        assert response.status_code == 200

        response = client.get(f"/conversations/{conv_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title_status"] == "fallback"
        assert data["title"] == "tell me about python"

    def test_persist_chat_messages_rejects_invalid_role(self):
        conv_resp = client.post("/chat/conversations")
        conv_id = conv_resp.json()["id"]

        response = client.post(
            f"/chat/conversations/{conv_id}/messages",
            json={"messages": [{"role": "tool", "content": "x"}]},
        )
        assert response.status_code == 422

    def test_chat_messages_not_found(self):
        response = client.get("/chat/conversations/nonexistent/messages")
        assert response.status_code == 404
