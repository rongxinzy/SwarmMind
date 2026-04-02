"""Smoke-test the temporary chat backend flow via FastAPI TestClient.

This script exercises the real HTTP endpoints with a stubbed GeneralAgent so
the mode contract, persistence, and streaming event translation can be
verified without external model calls.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from swarmmind.api import supervisor
from swarmmind.models import ConversationMode


class FakeGeneralAgent:
    """Deterministic DeerFlow stand-in for backend flow verification."""

    def __init__(self, *args, **kwargs):
        self._kwargs = kwargs

    def stream_events(self, goal: str, ctx=None, runtime_options=None):
        yield {
            "type": "assistant_reasoning",
            "message_id": "reasoning-1",
            "content": f"分析任务: {goal}",
        }
        yield {
            "type": "assistant_tool_calls",
            "message_id": "tools-1",
            "tool_calls": [
                {
                    "name": "task",
                    "args": {"description": "拆分任务"},
                    "id": "task-1",
                },
                {
                    "name": "search",
                    "args": {"query": "crm mvp"},
                    "id": "search-1",
                },
            ],
        }
        yield {
            "type": "tool_result",
            "message_id": "tool-msg-1",
            "tool_name": "task",
            "tool_call_id": "task-1",
            "content": "Task Succeeded. Result: 已完成拆分",
        }
        yield {
            "type": "tool_result",
            "message_id": "tool-msg-2",
            "tool_name": "search",
            "tool_call_id": "search-1",
            "content": "命中 3 个资料来源",
        }
        yield {
            "type": "assistant_message",
            "message_id": "assistant-1",
            "content": f"[{runtime_options.mode}] 已生成结果",
        }
        return f"[{runtime_options.mode}] 已生成结果", ["[search]: 命中 3 个资料来源"]


@contextmanager
def patched_backend() -> Iterator[None]:
    original_general_agent = supervisor.GeneralAgent
    original_derive_situation_tag = supervisor.derive_situation_tag
    original_title_generator = supervisor.generate_conversation_title_from_exchange
    original_db_path = os.environ.get("SWARMMIND_DB_PATH")

    with tempfile.TemporaryDirectory() as tempdir:
        os.environ["SWARMMIND_DB_PATH"] = os.path.join(tempdir, "smoke-test.db")
        supervisor.GeneralAgent = FakeGeneralAgent
        supervisor.derive_situation_tag = lambda _: "unknown"
        supervisor.generate_conversation_title_from_exchange = lambda user_message, assistant_message: (
            f"Smoke {user_message[:12]}",
            "llm",
        )
        try:
            yield
        finally:
            supervisor.GeneralAgent = original_general_agent
            supervisor.derive_situation_tag = original_derive_situation_tag
            supervisor.generate_conversation_title_from_exchange = original_title_generator
            if original_db_path is None:
                os.environ.pop("SWARMMIND_DB_PATH", None)
            else:
                os.environ["SWARMMIND_DB_PATH"] = original_db_path


def parse_json_lines(raw_text: str) -> list[dict]:
    return [json.loads(line) for line in raw_text.splitlines() if line.strip()]


def run_case(client: TestClient, *, label: str, payload: dict) -> dict:
    conversation_response = client.post(
        "/conversations",
        json={"goal": f"{label} 验证目标"},
    )
    conversation_response.raise_for_status()
    conversation = conversation_response.json()
    conversation_id = conversation["id"]

    stream_response = client.post(
        f"/conversations/{conversation_id}/messages/stream",
        json=payload,
    )
    stream_response.raise_for_status()
    events = parse_json_lines(stream_response.text)

    messages_response = client.get(f"/conversations/{conversation_id}/messages")
    messages_response.raise_for_status()
    messages = messages_response.json()["items"]

    summary = {
        "label": label,
        "conversation_id": conversation_id,
        "event_types": [event["type"] for event in events],
        "assistant_final": next(event for event in events if event["type"] == "assistant_final")["message"]["content"],
        "message_count": len(messages),
        "has_thinking": any(event["type"] == "thinking" for event in events),
        "has_team_task": any(event["type"] == "team_task" for event in events),
        "has_team_activity": any(event["type"] == "team_activity" for event in events),
    }
    return summary


def main() -> None:
    cases = [
        ("flash", {"content": "给我一版快速摘要", "mode": ConversationMode.FLASH.value}),
        ("thinking", {"content": "给我一版深度分析", "mode": ConversationMode.THINKING.value}),
        ("pro", {"content": "给我一版规划后执行的结果", "mode": ConversationMode.PRO.value}),
        ("ultra", {"content": "给我一版协作执行结果", "mode": ConversationMode.ULTRA.value}),
        ("legacy-reasoning", {"content": "兼容路径测试", "reasoning": True}),
    ]

    with patched_backend():
        with TestClient(supervisor.app) as client:
            print("Temporary chat backend smoke test")
            print("=" * 40)
            for label, payload in cases:
                result = run_case(client, label=label, payload=payload)
                print(f"CASE {result['label']}")
                print(f"  conversation_id: {result['conversation_id']}")
                print(f"  assistant_final: {result['assistant_final']}")
                print(f"  message_count: {result['message_count']}")
                print(f"  has_thinking: {result['has_thinking']}")
                print(f"  has_team_task: {result['has_team_task']}")
                print(f"  has_team_activity: {result['has_team_activity']}")
                print(f"  event_types: {', '.join(result['event_types'])}")
                print("-" * 40)


if __name__ == "__main__":
    main()
