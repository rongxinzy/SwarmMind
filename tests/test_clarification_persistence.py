"""Regression tests for clarification response persistence."""

from __future__ import annotations

from sqlalchemy import text

from swarmmind.api import supervisor
from swarmmind.db import init_db, seed_default_agents, session_scope
from swarmmind.models import CreateConversationRequest


def _message_columns() -> set[str]:
    with session_scope() as session:
        rows = session.exec(text("PRAGMA table_info(messages)")).all()
    return {str(row[1]) for row in rows}


def test_clarification_response_persists_as_tool_message_and_is_readable(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    init_db()
    seed_default_agents()

    columns = _message_columns()
    assert "tool_call_id" in columns
    assert "name" in columns

    conversation = supervisor.create_conversation(CreateConversationRequest(title="clarification 持久化回归"))
    result = supervisor.respond_to_clarification(
        conversation.id,
        supervisor.ClarificationResponseRequest(
            tool_call_id="clarify-001",
            response="范围锁定在 sales pipeline 与 reporting",
        ),
    )

    assert result.id
    assert result.role == "tool"
    assert result.content == "范围锁定在 sales pipeline 与 reporting"
    assert result.tool_call_id == "clarify-001"
    assert result.name == "ask_clarification_response"

    messages = supervisor.get_conversation_messages(conversation.id)
    assert messages.total == 1
    assert messages.items[0].id == result.id
    assert messages.items[0].role == "tool"
    assert messages.items[0].content == "范围锁定在 sales pipeline 与 reporting"
    assert messages.items[0].tool_call_id == "clarify-001"
    assert messages.items[0].name == "ask_clarification_response"

    with session_scope() as session:
        row = session.exec(
            text(
                """
                SELECT role, content, tool_call_id, name
                FROM messages
                WHERE id = :id
                """,
            ).bindparams(id=result.id),
        ).first()

    assert row is not None
    assert row[0] == "tool"
    assert row[1] == "范围锁定在 sales pipeline 与 reporting"
    assert row[2] == "clarify-001"
    assert isinstance(row[3], str) and row[3]
