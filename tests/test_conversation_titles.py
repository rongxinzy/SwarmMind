"""Tests for ChatSession title generation timing and persistence."""

import pytest

from swarmmind import context_broker
from swarmmind.api import supervisor
from swarmmind.db import get_connection, init_db, seed_default_agents
from swarmmind.models import GoalRequest, SendMessageRequest


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    """Use a temporary DB for each test."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("SWARMMIND_DB_PATH", db_path)
    init_db()
    seed_default_agents()
    yield


class FakeProposal:
    def __init__(self, description: str):
        self.description = description


class FakeDeerFlowRuntimeAdapter:
    def __init__(self, *args, **kwargs):
        pass

    def act(self, goal: str, proposal_id: str, ctx=None, runtime_options=None):
        return FakeProposal(f"Stub DeerFlow response for: {goal}")


def _conversation_row(conversation_id: str):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
        return cursor.fetchone()
    finally:
        conn.close()


class TestConversationTitles:
    def test_create_conversation_starts_with_pending_title(self):
        conversation = supervisor.create_conversation(
            GoalRequest(goal="帮我分析 CRM MVP 的模块边界"),
        )

        assert conversation.title == "New Conversation"
        assert conversation.title_status == "pending"
        assert conversation.title_source is None
        assert conversation.title_generated_at is None

    def test_first_complete_exchange_generates_title(self, monkeypatch):
        monkeypatch.setattr(supervisor, "DeerFlowRuntimeAdapter", FakeDeerFlowRuntimeAdapter)
        monkeypatch.setattr(supervisor, "derive_situation_tag", lambda _: "finance")
        monkeypatch.setattr(context_broker, "derive_situation_tag", lambda _: "finance")
        monkeypatch.setattr(
            supervisor,
            "_generate_title_with_deerflow",
            lambda user_message, assistant_message: ("CRM MVP 模块边界", "llm"),
        )

        conversation = supervisor.create_conversation(
            GoalRequest(goal="请分析 CRM MVP 的模块边界"),
        )
        response = supervisor.send_message(
            conversation.id,
            SendMessageRequest(content="请分析 CRM MVP 的模块边界", reasoning=False),
        )

        row = _conversation_row(conversation.id)
        assert response.assistant_message.content.startswith("Stub DeerFlow response")
        assert row["title"] == "CRM MVP 模块边界"
        assert row["title_status"] == "generated"
        assert row["title_source"] == "llm"
        assert row["title_generated_at"] is not None

    def test_subsequent_messages_do_not_regenerate_title(self, monkeypatch):
        calls: list[tuple[str, str]] = []

        monkeypatch.setattr(supervisor, "DeerFlowRuntimeAdapter", FakeDeerFlowRuntimeAdapter)
        monkeypatch.setattr(supervisor, "derive_situation_tag", lambda _: "finance")
        monkeypatch.setattr(context_broker, "derive_situation_tag", lambda _: "finance")

        def fake_title_generator(user_message: str, assistant_message: str):
            calls.append((user_message, assistant_message))
            return "CRM MVP 模块边界", "llm"

        monkeypatch.setattr(
            supervisor,
            "_generate_title_with_deerflow",
            fake_title_generator,
        )

        conversation = supervisor.create_conversation(
            GoalRequest(goal="请分析 CRM MVP 的模块边界"),
        )

        supervisor.send_message(
            conversation.id,
            SendMessageRequest(content="请分析 CRM MVP 的模块边界", reasoning=False),
        )
        supervisor.send_message(
            conversation.id,
            SendMessageRequest(content="继续展开销售线索和商机部分", reasoning=False),
        )

        row = _conversation_row(conversation.id)
        assert row["title"] == "CRM MVP 模块边界"
        assert row["title_status"] == "generated"
        assert len(calls) == 1

    def test_title_generation_falls_back_when_llm_fails(self, monkeypatch):
        monkeypatch.setattr(supervisor, "DeerFlowRuntimeAdapter", FakeDeerFlowRuntimeAdapter)
        monkeypatch.setattr(supervisor, "derive_situation_tag", lambda _: "finance")
        monkeypatch.setattr(context_broker, "derive_situation_tag", lambda _: "finance")

        def fake_title_generator(user_message: str, assistant_message: str):
            return "请分析 CRM MVP 的模块边界", "fallback"

        monkeypatch.setattr(
            supervisor,
            "_generate_title_with_deerflow",
            fake_title_generator,
        )

        conversation = supervisor.create_conversation(
            GoalRequest(goal="请分析 CRM MVP 的模块边界"),
        )
        supervisor.send_message(
            conversation.id,
            SendMessageRequest(content="请分析 CRM MVP 的模块边界", reasoning=False),
        )

        row = _conversation_row(conversation.id)
        assert row["title_status"] == "fallback"
        assert row["title_source"] == "fallback"
