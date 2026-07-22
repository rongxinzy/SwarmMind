"""Helpers for DeerFlow runtime stream capture and event normalization."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable, Generator
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage

logger = logging.getLogger(__name__)


@dataclass
class StreamCaptureState:
    """Mutable capture state for a single async DeerFlow turn."""

    current_chunk_msg_id: str | None = None
    accumulated_reasoning: str = ""
    accumulated_content: str = ""
    final_text: str = ""
    tool_results: list[str] = field(default_factory=list)
    seen_ids: set[str] = field(default_factory=set)
    last_todos: list[dict] | None = None


def _jsonable(value: Any) -> Any:
    """Return a JSON-safe copy without changing LangChain message semantics."""
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump())
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def _serialize_tool_call(tool_call: Any) -> dict[str, Any]:
    if isinstance(tool_call, dict):
        return {
            "name": str(tool_call.get("name") or ""),
            "args": _jsonable(tool_call.get("args") or {}),
            "id": tool_call.get("id"),
            "type": tool_call.get("type") or "tool_call",
        }
    return {
        "name": str(getattr(tool_call, "name", "") or ""),
        "args": _jsonable(getattr(tool_call, "args", {}) or {}),
        "id": getattr(tool_call, "id", None),
        "type": getattr(tool_call, "type", None) or "tool_call",
    }


def serialize_deerflow_message(
    message: object, extract_text: Callable[[object], str] | None = None
) -> dict[str, Any] | None:
    """Serialize a LangChain message into the flat LangGraph SDK Message shape."""
    if isinstance(message, HumanMessage):
        return {
            "type": "human",
            "id": getattr(message, "id", None),
            "name": getattr(message, "name", None),
            "content": _jsonable(getattr(message, "content", "")),
            "additional_kwargs": _jsonable(getattr(message, "additional_kwargs", {}) or {}),
            "response_metadata": _jsonable(getattr(message, "response_metadata", {}) or {}),
        }

    if isinstance(message, AIMessage | AIMessageChunk):
        native: dict[str, Any] = {
            "type": "ai",
            "id": getattr(message, "id", None),
            "name": getattr(message, "name", None),
            "content": _jsonable(getattr(message, "content", "")),
            "additional_kwargs": _jsonable(getattr(message, "additional_kwargs", {}) or {}),
            "response_metadata": _jsonable(getattr(message, "response_metadata", {}) or {}),
        }
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            native["tool_calls"] = [_serialize_tool_call(tool_call) for tool_call in tool_calls]
        invalid_tool_calls = getattr(message, "invalid_tool_calls", None)
        if invalid_tool_calls:
            native["invalid_tool_calls"] = _jsonable(invalid_tool_calls)
        usage_metadata = getattr(message, "usage_metadata", None)
        if usage_metadata:
            native["usage_metadata"] = _jsonable(usage_metadata)
        return native

    if isinstance(message, ToolMessage):
        content = getattr(message, "content", "")
        if extract_text is not None:
            content = extract_text(content)
        return {
            "type": "tool",
            "id": getattr(message, "id", None),
            "name": getattr(message, "name", None),
            "content": _jsonable(content),
            "tool_call_id": getattr(message, "tool_call_id", None),
            "status": getattr(message, "status", None) or "success",
            "additional_kwargs": _jsonable(getattr(message, "additional_kwargs", {}) or {}),
            "response_metadata": _jsonable(getattr(message, "response_metadata", {}) or {}),
        }

    return None


def _streaming_ai_message_event(capture_state: StreamCaptureState) -> dict[str, Any]:
    additional_kwargs: dict[str, Any] = {}
    if capture_state.accumulated_reasoning:
        additional_kwargs["reasoning_content"] = capture_state.accumulated_reasoning
    return {
        "type": "deerflow.message",
        "transient": True,
        "message": {
            "type": "ai",
            "id": capture_state.current_chunk_msg_id,
            "content": capture_state.accumulated_content,
            "additional_kwargs": additional_kwargs,
            "response_metadata": {},
        },
    }


def process_messages_mode_chunk(
    msg_chunk: object,
    capture_state: StreamCaptureState,
) -> list[dict[str, Any]]:
    """Convert a streaming AI chunk into accumulated reasoning/content events."""
    if not isinstance(msg_chunk, AIMessageChunk):
        return []

    chunk_id = getattr(msg_chunk, "id", None)
    if chunk_id and chunk_id != capture_state.current_chunk_msg_id:
        capture_state.current_chunk_msg_id = chunk_id
        capture_state.accumulated_reasoning = ""
        capture_state.accumulated_content = ""

    if not capture_state.current_chunk_msg_id:
        capture_state.current_chunk_msg_id = str(uuid.uuid4())

    events: list[dict[str, Any]] = []
    reasoning_delta = extract_reasoning_delta(msg_chunk)
    if reasoning_delta:
        capture_state.accumulated_reasoning += reasoning_delta
        events.append(
            {
                "type": "assistant_reasoning",
                "message_id": capture_state.current_chunk_msg_id,
                "content": capture_state.accumulated_reasoning,
            }
        )

    content_delta = extract_content_delta(msg_chunk)
    if content_delta:
        # 注意：accumulated_content 是累计完整内容，非增量片段。
        # 上层事件序列化时使用 content.accumulated 明确表达累计状态。
        capture_state.accumulated_content += content_delta
        events.append(
            {
                "type": "assistant_message",
                "message_id": capture_state.current_chunk_msg_id,
                "content": capture_state.accumulated_content,
            }
        )

    return events


def process_custom_mode_chunk(event: object) -> dict[str, Any] | None:
    """Normalize supported custom task events from DeerFlow."""
    logger.debug("Custom event received: %s", event)
    if not isinstance(event, dict) or event.get("type") not in {
        "task_started",
        "task_running",
        "task_completed",
        "task_failed",
        "plan_steps",
    }:
        return None

    logger.info("Task event: type=%s, task_id=%s", event.get("type"), event.get("task_id"))
    return {
        "type": "custom_event",
        "event_type": event["type"],
        "task_id": event.get("task_id"),
        "description": event.get("description"),
        "message": event.get("message"),
        "result": event.get("result"),
        "error": event.get("error"),
    }


def iter_new_turn_messages(
    messages: list[object],
    current_user_message_id: str,
    seen_ids: set[str],
) -> Generator[object, None, None]:
    """Yield unseen non-user messages after the current turn anchor."""
    turn_anchor_index = next(
        (
            index
            for index, message in enumerate(messages)
            if isinstance(message, HumanMessage) and getattr(message, "id", None) == current_user_message_id
        ),
        -1,
    )
    if turn_anchor_index == -1:
        return

    for msg in messages[turn_anchor_index + 1 :]:
        if isinstance(msg, HumanMessage):
            continue

        msg_id = getattr(msg, "id", None)
        if msg_id and msg_id in seen_ids:
            continue
        if msg_id:
            seen_ids.add(msg_id)
        yield msg


def process_values_mode_message(
    msg: object,
    capture_state: StreamCaptureState,
    extract_text: Callable[[object], str],
) -> list[dict[str, Any]]:
    """Convert full values-mode messages into runtime events and summaries."""
    msg_id = getattr(msg, "id", None)

    if isinstance(msg, AIMessage):
        events: list[dict[str, Any]] = []
        if msg.tool_calls:
            tool_names = [tc.get("name") for tc in msg.tool_calls]
            logger.info("AI tool calls: %s", tool_names)
            events.append(
                {
                    "type": "assistant_tool_calls",
                    "message_id": msg_id,
                    "tool_calls": [
                        {
                            "name": tool_call.get("name"),
                            "args": tool_call.get("args", {}),
                            "id": tool_call.get("id"),
                        }
                        for tool_call in msg.tool_calls
                    ],
                }
            )

        content = extract_text(msg.content)
        if content:
            capture_state.final_text = content
        return events

    if isinstance(msg, ToolMessage):
        tool_name = getattr(msg, "name", None) or "unknown"
        tool_content = extract_text(msg.content)
        logger.info(
            "Tool result: name=%s, content_preview=%s",
            tool_name,
            tool_content[:100] if tool_content else "(empty)",
        )
        if tool_content:
            capture_state.tool_results.append(f"[{tool_name}]: {tool_content[:200]}")

        return [
            {
                "type": "tool_result",
                "message_id": msg_id,
                "tool_name": tool_name,
                "tool_call_id": getattr(msg, "tool_call_id", None),
                "content": tool_content,
            }
        ]

    return []


def extract_reasoning_delta(chunk: AIMessageChunk) -> str | None:
    """Extract incremental reasoning content from a streaming chunk."""
    additional_kwargs = getattr(chunk, "additional_kwargs", None) or {}
    reasoning = additional_kwargs.get("reasoning_content")
    if isinstance(reasoning, str) and reasoning:
        return reasoning

    content = getattr(chunk, "content", None)
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "thinking":
                thinking = block.get("thinking", "")
                if thinking:
                    return thinking

    return None


def process_values_mode_state(
    state: dict,
    capture_state: StreamCaptureState,
) -> list[dict[str, Any]]:
    """Extract todo list changes from a values-mode state snapshot.

    Returns normalized plan_steps events when the todo list has changed.
    """
    todos = state.get("todos")
    if not isinstance(todos, list):
        return []

    # Normalize todo items to a comparable form
    normalized = [
        {
            "description": str(item.get("description", "")),
            "status": str(item.get("status", "pending")),
        }
        for item in todos
        if isinstance(item, dict)
    ]

    if capture_state.last_todos == normalized:
        return []

    capture_state.last_todos = normalized
    if not normalized:
        return []

    return [{"type": "plan_steps", "steps": normalized}]


def extract_content_delta(chunk: AIMessageChunk) -> str | None:
    """Extract incremental text content from a streaming chunk."""
    content = getattr(chunk, "content", None)
    if isinstance(content, str) and content:
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                if text:
                    parts.append(text)
        return "".join(parts) if parts else None
    return None
