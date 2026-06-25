"""AI SDK compatible chat endpoint for the new ai-elements frontend.

This module provides:
- POST /api/chat        : streaming chat turn that emits UIMessage-friendly NDJSON.
- GET  /api/chat/history: load persisted messages as UIMessage array.

The existing /conversations/{id}/messages/stream endpoint is kept for backward
compatibility; new UI code should consume this module exclusively.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Generator
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from swarmmind.models import ConversationMode, SendMessageRequest


class ChatMessagePart(BaseModel):
    """A single part inside an AI SDK UIMessage."""

    type: str
    text: str | None = None
    state: str | None = None


class ChatMessage(BaseModel):
    """AI SDK UIMessage shape used for request/response."""

    id: str | None = None
    role: str
    content: str | None = None
    parts: list[ChatMessagePart] = Field(default_factory=list)


class ChatRequest(BaseModel):
    """Request body for POST /api/chat."""

    messages: list[ChatMessage] = Field(default_factory=list)
    conversation_id: str | None = None
    project_id: str | None = None
    mode: str | None = "flash"
    model_name: str | None = None


class HistoryResponse(BaseModel):
    """Response for GET /api/chat/history."""

    messages: list[ChatMessage]
    conversation_id: str


@dataclass(frozen=True)
class ChatRouterDeps:
    """Dependencies for the chat router."""

    conversation_repo: Any
    project_repo: Any
    conversation_support: Any
    stream_conversation_message: Callable[[str, SendMessageRequest], Generator[str, None, None]]
    stream_project_message: Callable[[str, str, SendMessageRequest], Generator[str, None, None]]
    resolve_runtime_options: Callable[[SendMessageRequest], Any]


def _parse_mode(mode: str | None) -> ConversationMode:
    """Normalize a mode string to a ConversationMode enum value."""
    if not mode:
        return ConversationMode.FLASH
    try:
        return ConversationMode(mode)
    except ValueError:
        return ConversationMode.FLASH


def _ensure_project_conversation(project_id: str, deps: ChatRouterDeps) -> str:
    """Return the conversation_id attached to a project, creating one if needed."""
    from swarmmind.db import session_scope
    from swarmmind.db_models import ProjectDB

    proj = deps.project_repo.get_by_id(project_id)
    if proj.conversation_id:
        deps.conversation_repo.mark_project_bound(proj.conversation_id)
        return proj.conversation_id
    conv = deps.conversation_repo.create(title=proj.title, title_status="pending")
    deps.conversation_repo.mark_project_bound(conv.id)
    with session_scope() as session:
        proj_db = session.get(ProjectDB, project_id)
        if proj_db is not None:
            proj_db.conversation_id = conv.id
            session.commit()
    return conv.id


def _history_to_ui_messages(messages: list[Any]) -> list[ChatMessage]:
    """Convert persisted SwarmMind messages to UIMessage shape."""
    ui_messages: list[ChatMessage] = []
    for msg in messages:
        if msg.role not in ("user", "assistant"):
            continue
        ui_messages.append(
            ChatMessage(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                parts=[ChatMessagePart(type="text", text=msg.content, state="done")],
            )
        )
    return ui_messages


def _serialize(event_type: str, payload: dict[str, Any]) -> str:
    return json.dumps({"type": event_type, **payload}, ensure_ascii=False) + "\n"


def _translate_stream_event(event: dict[str, Any]) -> list[dict[str, Any]]:
    """Translate a SwarmMind NDJSON event into ai-elements friendly events.

    The returned list contains small delta events that the frontend uses to
    build/update a UIMessage array.
    """
    event_type = event.get("type")

    if event_type == "user_message":
        msg = event.get("message", {})
        return [
            {
                "type": "user_message",
                "message": {
                    "id": msg.get("id"),
                    "role": "user",
                    "content": msg.get("content"),
                    "parts": [{"type": "text", "text": msg.get("content"), "state": "done"}],
                },
            }
        ]

    if event_type == "content.accumulated":
        return [
            {
                "type": "text_delta",
                "text": event.get("text", ""),
                "state": "streaming",
            }
        ]

    if event_type == "status.thinking":
        return [
            {
                "type": "reasoning_delta",
                "text": event.get("text", ""),
                "state": "streaming",
            }
        ]

    if event_type == "thinking":
        return [
            {
                "type": "reasoning_delta",
                "text": event.get("content", ""),
                "state": "streaming",
            }
        ]

    if event_type == "assistant_final":
        msg = event.get("message", {})
        return [
            {
                "type": "assistant_done",
                "message": {
                    "id": msg.get("id"),
                    "role": "assistant",
                    "content": msg.get("content"),
                    "parts": [{"type": "text", "text": msg.get("content"), "state": "done"}],
                },
            }
        ]

    if event_type == "task_started":
        task = event.get("task", {})
        tool_id = task.get("id") or str(uuid.uuid4())
        return [
            {
                "type": "tool_call",
                "tool_call_id": tool_id,
                "tool_name": "swarmmind_task",
                "state": "input-available",
                "input": {"description": task.get("description", "")},
            }
        ]

    if event_type == "task_running":
        task = event.get("task", {})
        tool_id = task.get("id") or str(uuid.uuid4())
        return [
            {
                "type": "tool_call",
                "tool_call_id": tool_id,
                "tool_name": "swarmmind_task",
                "state": "input-available",
                "input": {"description": task.get("message", task.get("description", ""))},
            }
        ]

    if event_type == "task_completed":
        task = event.get("task", {})
        tool_id = task.get("id") or str(uuid.uuid4())
        return [
            {
                "type": "tool_result",
                "tool_call_id": tool_id,
                "tool_name": "swarmmind_task",
                "state": "output-available",
                "output": {"result": task.get("result", "")},
            }
        ]

    if event_type == "task_failed":
        task = event.get("task", {})
        tool_id = task.get("id") or str(uuid.uuid4())
        return [
            {
                "type": "tool_result",
                "tool_call_id": tool_id,
                "tool_name": "swarmmind_task",
                "state": "output-error",
                "output": {"error": task.get("error", "")},
            }
        ]

    if event_type == "status.artifact":
        return [
            {
                "type": "artifact",
                "artifact_type": event.get("artifact_type"),
                "name": event.get("name"),
            }
        ]

    if event_type == "status.clarification":
        tool_id = str(uuid.uuid4())
        return [
            {
                "type": "tool_call",
                "tool_call_id": tool_id,
                "tool_name": "ask_clarification",
                "state": "input-available",
                "input": {"question": event.get("question", "")},
            }
        ]

    if event_type == "status.waiting_approval":
        return [
            {
                "type": "approval_request",
                "approval_id": event.get("approval_id"),
                "capability": event.get("capability"),
                "risk_tier": event.get("risk_tier"),
                "run_id": event.get("run_id"),
                "project_id": event.get("project_id"),
            }
        ]

    if event_type == "error":
        return [
            {
                "type": "error",
                "code": event.get("code"),
                "message": event.get("message"),
            }
        ]

    if event_type == "done":
        return [{"type": "done"}]

    return []


def _stream_chat(deps: ChatRouterDeps, body: ChatRequest) -> Generator[str, None, None]:
    """Core streaming generator for POST /api/chat."""
    conversation_id = body.conversation_id
    project_id = body.project_id

    if project_id:
        conversation_id = _ensure_project_conversation(project_id, deps)
    elif not conversation_id:
        # Start a new conversation from the last user message text.
        last_user_text = ""
        for msg in reversed(body.messages):
            if msg.role == "user":
                for part in msg.parts:
                    if part.type == "text" and part.text:
                        last_user_text = part.text
                        break
                if last_user_text:
                    break
        title = (last_user_text[:50] + "...") if len(last_user_text) > 50 else (last_user_text or "New Chat")
        conv = deps.conversation_repo.create(title=title, title_status="pending")
        conversation_id = conv.id

    if conversation_id is None:
        yield _serialize("error", {"code": "BAD_REQUEST", "message": "No conversation_id available"})
        return

    # Pull the latest user text from the request.
    user_text = ""
    for msg in reversed(body.messages):
        if msg.role == "user":
            for part in msg.parts:
                if part.type == "text" and part.text:
                    user_text = part.text
                    break
            if user_text:
                break

    if not user_text.strip():
        yield _serialize("error", {"code": "BAD_REQUEST", "message": "User message text is required"})
        return

    send_request = SendMessageRequest(
        content=user_text,
        mode=_parse_mode(body.mode),
        model_name=body.model_name,
    )

    # Emit conversation id and initial assistant message shell.
    assistant_id = str(uuid.uuid4())
    yield _serialize("conversation_start", {"conversation_id": conversation_id})
    yield _serialize(
        "assistant_start",
        {"message": {"id": assistant_id, "role": "assistant", "content": "", "parts": []}},
    )

    try:
        if project_id:
            raw_stream = deps.stream_project_message(project_id, conversation_id, send_request)
        else:
            raw_stream = deps.stream_conversation_message(conversation_id, send_request)

        for raw_line in raw_stream:
            line = raw_line.strip() if isinstance(raw_line, str) else ""
            if not line:
                continue
            try:
                raw_event = json.loads(line)
            except json.JSONDecodeError:
                continue
            for ui_event in _translate_stream_event(raw_event):
                yield _serialize(ui_event["type"], {k: v for k, v in ui_event.items() if k != "type"})
    except HTTPException:
        raise
    except Exception as exc:
        yield _serialize("error", {"code": "STREAM_ERROR", "message": str(exc)})


def build_chat_router(deps: ChatRouterDeps) -> APIRouter:
    """Build the AI SDK compatible chat router."""
    router = APIRouter(prefix="/api")

    @router.post("/chat", tags=["chat"])
    def chat(body: ChatRequest) -> StreamingResponse:
        """Stream a chat turn as UIMessage-friendly NDJSON events."""
        return StreamingResponse(
            _stream_chat(deps, body),
            media_type="application/x-ndjson",
        )

    @router.get("/chat/history", tags=["chat"])
    def chat_history(conversation_id: str) -> HistoryResponse:
        """Return persisted messages for a conversation as UIMessage array."""
        deps.conversation_repo.get_by_id(conversation_id)
        rows = deps.conversation_support.message_repo.list_by_conversation(conversation_id)
        return HistoryResponse(
            messages=_history_to_ui_messages(rows),
            conversation_id=conversation_id,
        )

    return router
