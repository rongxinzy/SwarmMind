"""Tests for GET /conversations/recent."""

from __future__ import annotations

import pytest

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


def test_recent_returns_204_when_no_conversations():
    response = supervisor.get_recent_conversation()
    # build_conversation_router wraps None as Response(status_code=204)
    from fastapi.responses import Response

    assert isinstance(response, Response)
    assert response.status_code == 204


def test_recent_returns_204_for_empty_conversation_without_messages():
    _ = supervisor.create_conversation(GoalRequest(goal="空会话"))
    response = supervisor.get_recent_conversation()
    from fastapi.responses import Response

    assert isinstance(response, Response)
    assert response.status_code == 204


def test_recent_returns_conversation_with_messages():
    conv = supervisor.create_conversation(GoalRequest(goal="活跃会话"))
    supervisor.send_message(conv.id, SendMessageRequest(content="hello"))

    result = supervisor.get_recent_conversation()
    assert result is not None
    assert result.conversation.id == conv.id
    assert len(result.messages) == 2  # user + assistant
    assert result.messages[0].role == "user"
    assert result.messages[1].role == "assistant"


def test_recent_returns_most_recently_updated_conversation():
    conv1 = supervisor.create_conversation(GoalRequest(goal="第一条"))
    supervisor.send_message(conv1.id, SendMessageRequest(content="msg1"))

    conv2 = supervisor.create_conversation(GoalRequest(goal="第二条"))
    supervisor.send_message(conv2.id, SendMessageRequest(content="msg2"))

    result = supervisor.get_recent_conversation()
    assert result is not None
    assert result.conversation.id == conv2.id
    assert len(result.messages) == 2


def test_recent_ignores_conversations_older_than_7_days():
    from datetime import timedelta

    from swarmmind.db import session_scope
    from swarmmind.db_models import ConversationDB, MessageDB
    from swarmmind.time_utils import utc_now

    conv = supervisor.create_conversation(GoalRequest(goal="旧会话"))

    # Backdate the conversation and its messages to 8 days ago
    from sqlmodel import select

    with session_scope() as session:
        db_conv = session.get(ConversationDB, conv.id)
        db_conv.updated_at = utc_now() - timedelta(days=8)
        db_conv.created_at = utc_now() - timedelta(days=8)
        for msg in session.exec(select(MessageDB).where(MessageDB.conversation_id == conv.id)).all():
            msg.created_at = utc_now() - timedelta(days=8)

    response = supervisor.get_recent_conversation()
    from fastapi.responses import Response

    assert isinstance(response, Response)
    assert response.status_code == 204
