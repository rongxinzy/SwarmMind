"""Tests for ChatSession streaming events and persistence."""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.requires_llm

from swarmmind.api import supervisor
from swarmmind.db import init_db, seed_default_agents
from swarmmind.models import ConversationMode, GoalRequest, SendMessageRequest


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("SWARMMIND_DB_PATH", db_path)
    init_db()
    seed_default_agents()
    yield


class FakeDeerFlowRuntimeAdapter:
    init_calls: list[dict] = []
    stream_runtime_options: list[object] = []

    def __init__(self, *args, **kwargs):
        self.__class__.init_calls.append(kwargs)

    def stream_events(self, goal: str, ctx=None, runtime_options=None):
        self.__class__.stream_runtime_options.append(runtime_options)
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


@pytest.fixture(autouse=True)
def reset_fake_general_agent():
    FakeDeerFlowRuntimeAdapter.init_calls = []
    FakeDeerFlowRuntimeAdapter.stream_runtime_options = []
    yield


def _conversation_message_count(conversation_id: str) -> int:
    from sqlalchemy import func
    from sqlmodel import select

    from swarmmind.db import get_session
    from swarmmind.db_models import MessageDB

    session = get_session()
    try:
        return session.exec(select(func.count(MessageDB.id)).where(MessageDB.conversation_id == conversation_id)).one()
    finally:
        session.close()


def _conversation_row(conversation_id: str):
    from swarmmind.db import get_session
    from swarmmind.db_models import ConversationDB

    session = get_session()
    try:
        return session.get(ConversationDB, conversation_id)
    finally:
        session.close()


def test_streaming_chat_session_emits_runtime_events_and_persists_messages(monkeypatch):
    monkeypatch.setattr(supervisor, "DeerFlowRuntimeAdapter", FakeDeerFlowRuntimeAdapter)
    monkeypatch.setattr(supervisor, "derive_situation_tag", lambda _: "unknown")
    monkeypatch.setattr(
        supervisor,
        "_generate_title_with_deerflow",
        lambda user_message, assistant_message: ("CRM 探索", "llm"),
    )

    conversation = supervisor.create_conversation(
        GoalRequest(goal="帮我分析 CRM MVP 应该怎么做"),
    )

    raw_lines = list(
        supervisor._stream_conversation_message(
            conversation.id,
            SendMessageRequest(content="帮我分析 CRM MVP 应该怎么做", mode=ConversationMode.ULTRA),
        ),
    )
    events = [json.loads(line) for line in raw_lines]

    assert events[0]["type"] == "status"
    assert any(event["type"] == "thinking" for event in events)
    assert any(event["type"] == "assistant_message" for event in events)
    assert any(
        event["type"] == "team_task" and event["task"]["id"] == "task-1" and event["task"]["status"] == "running"
        for event in events
    )
    assert any(
        event["type"] == "team_task" and event["task"]["id"] == "task-1" and event["task"]["status"] == "completed"
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
    assert FakeDeerFlowRuntimeAdapter.stream_runtime_options[-1].mode == ConversationMode.ULTRA
    conversation_row = _conversation_row(conversation.id)
    assert conversation_row.runtime_profile_id == "local-default"
    assert conversation_row.runtime_instance_id == "local-default-instance"
    assert conversation_row.thread_id == conversation.id


@pytest.mark.parametrize(
    (
        "message_request",
        "expected_mode",
        "expected_thinking",
        "expected_plan",
        "expected_subagents",
    ),
    [
        (
            SendMessageRequest(content="flash", mode=ConversationMode.FLASH),
            ConversationMode.FLASH,
            False,
            False,
            False,
        ),
        (
            SendMessageRequest(content="thinking", mode=ConversationMode.THINKING),
            ConversationMode.THINKING,
            True,
            False,
            False,
        ),
        (
            SendMessageRequest(content="pro", mode=ConversationMode.PRO),
            ConversationMode.PRO,
            True,
            True,
            False,
        ),
        (
            SendMessageRequest(content="ultra", mode=ConversationMode.ULTRA),
            ConversationMode.ULTRA,
            True,
            True,
            True,
        ),
        (
            SendMessageRequest(content="legacy-thinking", reasoning=True),
            ConversationMode.THINKING,
            True,
            False,
            False,
        ),
        (
            SendMessageRequest(content="legacy-flash", reasoning=False),
            ConversationMode.FLASH,
            False,
            False,
            False,
        ),
    ],
)
def test_resolve_runtime_options(message_request, expected_mode, expected_thinking, expected_plan, expected_subagents):
    runtime_options = supervisor._resolve_runtime_options(message_request)

    assert runtime_options.mode == expected_mode
    assert runtime_options.thinking_enabled is expected_thinking
    assert runtime_options.plan_mode is expected_plan
    assert runtime_options.subagent_enabled is expected_subagents


def test_flash_mode_suppresses_reasoning_and_team_events(monkeypatch):
    monkeypatch.setattr(supervisor, "DeerFlowRuntimeAdapter", FakeDeerFlowRuntimeAdapter)
    monkeypatch.setattr(supervisor, "derive_situation_tag", lambda _: "unknown")

    conversation = supervisor.create_conversation(
        GoalRequest(goal="快速给我一版摘要"),
    )

    raw_lines = list(
        supervisor._stream_conversation_message(
            conversation.id,
            SendMessageRequest(content="快速给我一版摘要", mode=ConversationMode.FLASH),
        ),
    )
    events = [json.loads(line) for line in raw_lines]

    assert not any(event["type"] == "thinking" for event in events)
    assert not any(event["type"] == "team_task" for event in events)
    assert not any(event["type"] == "team_activity" for event in events)
    assert any(event["type"] == "assistant_final" for event in events)
    assert FakeDeerFlowRuntimeAdapter.stream_runtime_options[-1].mode == ConversationMode.FLASH


def test_reasoning_compatibility_uses_thinking_mode_without_team_events(monkeypatch):
    monkeypatch.setattr(supervisor, "DeerFlowRuntimeAdapter", FakeDeerFlowRuntimeAdapter)
    monkeypatch.setattr(supervisor, "derive_situation_tag", lambda _: "unknown")

    conversation = supervisor.create_conversation(
        GoalRequest(goal="帮我展开分析"),
    )

    raw_lines = list(
        supervisor._stream_conversation_message(
            conversation.id,
            SendMessageRequest(content="帮我展开分析", reasoning=True),
        ),
    )
    events = [json.loads(line) for line in raw_lines]

    assert any(event["type"] == "thinking" for event in events)
    assert not any(event["type"] == "team_task" for event in events)
    assert not any(event["type"] == "team_activity" for event in events)
    assert FakeDeerFlowRuntimeAdapter.stream_runtime_options[-1].mode == ConversationMode.THINKING
