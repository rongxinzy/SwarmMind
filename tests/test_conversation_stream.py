"""Tests for ChatSession streaming events and persistence."""

from __future__ import annotations

import json

import pytest

from swarmmind.api import supervisor
from swarmmind.db import get_connection, init_db, seed_default_agents
from swarmmind.models import GoalRequest, SendMessageRequest


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("SWARMMIND_DB_PATH", db_path)
    init_db()
    seed_default_agents()
    yield


class FakeGeneralAgent:
    def __init__(self, *args, **kwargs):
        pass

    def stream_events(self, goal: str, ctx=None):
        yield {
            "type": "assistant_reasoning",
            "message_id": "reasoning-1",
            "content": "先拆解问题，再安排协作。",
        }
        yield {
            "type": "assistant_tool_calls",
            "message_id": "tools-1",
            "tool_calls": [
                {
                    "name": "task",
                    "args": {"description": "收集竞品资料"},
                    "id": "task-1",
                },
                {
                    "name": "search",
                    "args": {"query": "crm mvp competitors"},
                    "id": "search-1",
                },
            ],
        }
        yield {
            "type": "tool_result",
            "message_id": "tool-msg-1",
            "tool_name": "task",
            "tool_call_id": "task-1",
            "content": "Task Succeeded. Result: 已完成竞品资料汇总",
        }
        yield {
            "type": "tool_result",
            "message_id": "tool-msg-2",
            "tool_name": "search",
            "tool_call_id": "search-1",
            "content": "找到了 5 个相关来源",
        }
        yield {
            "type": "assistant_message",
            "message_id": "assistant-1",
            "content": "这是 DeerFlow 流式返回的最终回答。",
        }
        return "这是 DeerFlow 流式返回的最终回答。", ["[search]: 找到了 5 个相关来源"]


def _conversation_message_count(conversation_id: str) -> int:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) AS total FROM messages WHERE conversation_id = ?",
            (conversation_id,),
        )
        return int(cursor.fetchone()["total"])
    finally:
        conn.close()


def test_streaming_chat_session_emits_runtime_events_and_persists_messages(monkeypatch):
    monkeypatch.setattr(supervisor, "GeneralAgent", FakeGeneralAgent)
    monkeypatch.setattr(supervisor, "derive_situation_tag", lambda _: "unknown")
    monkeypatch.setattr(
        supervisor,
        "generate_conversation_title_from_exchange",
        lambda user_message, assistant_message: ("CRM 探索", "llm"),
    )

    conversation = supervisor.create_conversation(
        GoalRequest(goal="帮我分析 CRM MVP 应该怎么做"),
    )

    raw_lines = list(
        supervisor._stream_conversation_message(
            conversation.id,
            SendMessageRequest(content="帮我分析 CRM MVP 应该怎么做", reasoning=True),
        ),
    )
    events = [json.loads(line) for line in raw_lines]

    assert events[0]["type"] == "status"
    assert any(event["type"] == "thinking" for event in events)
    assert any(event["type"] == "assistant_message" for event in events)
    assert any(
        event["type"] == "team_task"
        and event["task"]["id"] == "task-1"
        and event["task"]["status"] == "running"
        for event in events
    )
    assert any(
        event["type"] == "team_task"
        and event["task"]["id"] == "task-1"
        and event["task"]["status"] == "completed"
        for event in events
    )
    assert any(
        event["type"] == "team_activity"
        and event["activity"]["id"] == "search-1"
        and event["activity"]["status"] == "running"
        for event in events
    )
    assert any(
        event["type"] == "team_activity"
        and event["activity"]["id"] == "search-1"
        and event["activity"]["status"] == "completed"
        for event in events
    )
    assert events[-1]["type"] == "done"

    assistant_final = next(event for event in events if event["type"] == "assistant_final")
    title_event = next(event for event in events if event["type"] == "title")

    assert assistant_final["message"]["content"] == "这是 DeerFlow 流式返回的最终回答。"
    assert title_event["conversation"]["title"] == "CRM 探索"
    assert title_event["conversation"]["title_status"] == "generated"
    assert _conversation_message_count(conversation.id) == 2
