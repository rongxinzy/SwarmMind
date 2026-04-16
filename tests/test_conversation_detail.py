"""Tests for conversation detail and delete endpoints."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from swarmmind.api import supervisor
from swarmmind.db import init_db, seed_default_agents
from swarmmind.models import GoalRequest, SendMessageRequest


class FakeDeerFlowRuntimeAdapter:
    def __init__(self, *args, **kwargs):
        pass

    def act(self, goal: str, proposal_id: str, ctx=None, runtime_options=None):
        from types import SimpleNamespace

        return SimpleNamespace(description=f"Fake response for: {goal}")


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setattr(supervisor, "DeerFlowRuntimeAdapter", FakeDeerFlowRuntimeAdapter)
    monkeypatch.setattr(supervisor, "derive_situation_tag", lambda _: "unknown")
    init_db()
    seed_default_agents()
    yield


class TestGetConversationDetail:
    def test_default_behavior_does_not_include_messages(self):
        conv = supervisor.create_conversation(GoalRequest(goal="测试"))
        supervisor.send_message(conv.id, SendMessageRequest(content="hello"))

        result = supervisor.get_conversation(conv.id, include_messages=False)
        assert result.id == conv.id
        assert result.messages is None

    def test_include_messages_returns_message_list(self):
        conv = supervisor.create_conversation(GoalRequest(goal="测试"))
        supervisor.send_message(conv.id, SendMessageRequest(content="hello"))

        result = supervisor.get_conversation(conv.id, include_messages=True)
        assert result.id == conv.id
        assert result.messages is not None
        assert len(result.messages) == 2
        assert result.messages[0].role == "user"
        assert result.messages[1].role == "assistant"

    def test_not_found_raises_404(self):
        with pytest.raises(HTTPException) as exc_info:
            supervisor.get_conversation("nonexistent-id", include_messages=True)
        assert exc_info.value.status_code == 404


class TestDeleteConversation:
    def test_delete_returns_next_conversation_id(self):
        conv1 = supervisor.create_conversation(GoalRequest(goal="第一条"))
        supervisor.send_message(conv1.id, SendMessageRequest(content="msg1"))

        conv2 = supervisor.create_conversation(GoalRequest(goal="第二条"))
        supervisor.send_message(conv2.id, SendMessageRequest(content="msg2"))

        # Delete the most recent one (conv2); next should be conv1
        result = supervisor.delete_conversation(conv2.id)
        assert result.status == "deleted"
        assert result.id == conv2.id
        assert result.next_conversation_id == conv1.id

        # conv2 should be gone
        with pytest.raises(HTTPException) as exc_info:
            supervisor.get_conversation(conv2.id)
        assert exc_info.value.status_code == 404

    def test_delete_last_conversation_returns_null_next_id(self):
        conv = supervisor.create_conversation(GoalRequest(goal="唯一"))
        supervisor.send_message(conv.id, SendMessageRequest(content="msg"))

        result = supervisor.delete_conversation(conv.id)
        assert result.status == "deleted"
        assert result.id == conv.id
        assert result.next_conversation_id is None

    def test_delete_not_found_raises_404(self):
        with pytest.raises(HTTPException) as exc_info:
            supervisor.delete_conversation("nonexistent-id")
        assert exc_info.value.status_code == 404
