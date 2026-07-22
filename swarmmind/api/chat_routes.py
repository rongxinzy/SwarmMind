"""DeerFlow-native chat endpoint for the Next.js frontend.

This module provides:
- POST /api/chat        : streaming chat turn that emits DeerFlow-native NDJSON.
- GET  /api/chat/history: load persisted messages as LangGraph Message arrays.

The older /conversations/{id}/messages/stream endpoint is kept for CLI and API
stability; new UI code should consume this module exclusively.
"""

from __future__ import annotations

import json
import logging
import mimetypes
import re
import uuid
from collections.abc import Callable, Generator
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from swarmmind.models import ConversationMode, SendMessageRequest
from swarmmind.services.artifact_content import (
    VIRTUAL_PATH_PREFIX,
    build_artifact_file_response,
    is_virtual_user_data_path,
    normalize_virtual_path,
    resolve_virtual_artifact_path,
)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
_SAFE_UPLOAD_FILENAME_RE = re.compile(r"[^A-Za-z0-9._ -]+")
logger = logging.getLogger(__name__)


class ChatMessagePart(BaseModel):
    """A text part accepted from already-open browser sessions."""

    type: str
    text: str | None = None
    state: str | None = None


class ChatMessage(BaseModel):
    """LangGraph SDK Message shape used by the native DeerFlow UI path.

    role/parts fields are accepted only so already-open clients can still post
    their latest user turn while the UI uses native messages.
    """

    id: str | None = None
    type: str | None = None
    role: str | None = None
    content: Any = ""
    name: str | None = None
    additional_kwargs: dict[str, Any] = Field(default_factory=dict)
    response_metadata: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[dict[str, Any]] | None = None
    invalid_tool_calls: list[dict[str, Any]] | None = None
    usage_metadata: dict[str, Any] | None = None
    tool_call_id: str | None = None
    status: str | None = None
    parts: list[ChatMessagePart] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class ChatRequest(BaseModel):
    """Request body for POST /api/chat.

    messages use the LangGraph SDK Message shape. role/parts input is still
    accepted so already-open browsers can finish their current turn.
    """

    messages: list[ChatMessage] = Field(default_factory=list)
    conversation_id: str | None = None
    project_id: str | None = None
    mode: str | None = "flash"
    model_name: str | None = None


class HistoryResponse(BaseModel):
    """Response for GET /api/chat/history."""

    messages: list[ChatMessage]
    conversation_id: str
    artifacts: list[str] = Field(default_factory=list)


class UploadedFileInfo(BaseModel):
    """A file uploaded into a DeerFlow thread user-data directory."""

    filename: str
    size: int
    path: str
    virtual_path: str
    artifact_url: str
    extension: str | None = None
    modified: float | None = None
    mime_type: str | None = None


class UploadResponse(BaseModel):
    """Response for POST /api/threads/{thread_id}/uploads."""

    success: bool
    files: list[UploadedFileInfo]
    message: str


class ListUploadsResponse(BaseModel):
    """Response for GET /api/threads/{thread_id}/uploads/list."""

    files: list[UploadedFileInfo]
    count: int


class SuggestionMessage(BaseModel):
    """Plain text message used to generate DeerFlow follow-up suggestions."""

    role: str = Field(..., description="Message role: user|assistant")
    content: str = Field(..., description="Message content as plain text")


class SuggestionsRequest(BaseModel):
    """Request body for DeerFlow follow-up suggestion generation."""

    messages: list[SuggestionMessage] = Field(..., description="Recent conversation messages")
    n: int = Field(default=3, ge=1, le=5, description="Number of suggestions to generate")
    model_name: str | None = Field(default=None, description="Optional model override")


class SuggestionsResponse(BaseModel):
    """Short follow-up questions the user might ask next."""

    suggestions: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class ChatRouterDeps:
    """Dependencies for the chat router."""

    conversation_repo: Any
    project_repo: Any
    conversation_support: Any
    artifact_repo: Any
    stream_native_conversation_message: Callable[[str, SendMessageRequest], Generator[str, None, None]]
    stream_native_project_message: Callable[[str, str, SendMessageRequest], Generator[str, None, None]]
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
    """Convert persisted SwarmMind messages to LangGraph Message shape."""
    ui_messages: list[ChatMessage] = []
    for msg in messages:
        native_payload = getattr(msg, "native_payload", None)
        if isinstance(native_payload, dict) and native_payload.get("type"):
            ui_messages.append(ChatMessage(**native_payload))
            continue

        if msg.role not in ("user", "assistant"):
            continue
        message_type = "human" if msg.role == "user" else "ai"
        ui_messages.append(
            ChatMessage(
                id=msg.id,
                type=message_type,
                role=msg.role,
                content=msg.content,
                additional_kwargs={},
                response_metadata={},
            )
        )
    return ui_messages


def _conversation_artifact_paths(deps: ChatRouterDeps, conversation_id: str) -> list[str]:
    """Return registered DeerFlow user-data artifact paths for a conversation."""
    paths: list[str] = []
    seen: set[str] = set()
    for artifact in deps.artifact_repo.list_by_conversation(conversation_id):
        raw_path = getattr(artifact, "path", None) or getattr(artifact, "name", None)
        normalized = normalize_virtual_path(raw_path)
        if not normalized or not is_virtual_user_data_path(normalized) or normalized in seen:
            continue
        seen.add(normalized)
        paths.append(normalized)
    return paths


def _serialize(event_type: str, payload: dict[str, Any]) -> str:
    return json.dumps({"type": event_type, **payload}, ensure_ascii=False) + "\n"


def _safe_upload_filename(filename: str | None) -> str:
    raw_name = Path(filename or "").name.replace("\x00", "").strip()
    safe_name = _SAFE_UPLOAD_FILENAME_RE.sub("_", raw_name).strip(" .")
    return safe_name or f"upload-{uuid.uuid4().hex[:8]}"


def _upload_virtual_path(filename: str) -> str:
    return f"{VIRTUAL_PATH_PREFIX}/uploads/{filename}"


def _artifact_url(thread_id: str, virtual_path: str) -> str:
    normalized = (normalize_virtual_path(virtual_path) or virtual_path).lstrip("/")
    encoded_path = "/".join(quote(part) for part in normalized.split("/"))
    return f"/conversations/{quote(thread_id)}/artifacts/{encoded_path}"


def _uploaded_file_info(thread_id: str, filename: str, virtual_path: str, size: int, mime_type: str | None = None) -> UploadedFileInfo:
    resolved_path = resolve_virtual_artifact_path(thread_id, virtual_path)
    extension = Path(filename).suffix.removeprefix(".") or None
    modified = resolved_path.stat().st_mtime if resolved_path.exists() else None
    return UploadedFileInfo(
        filename=filename,
        size=size,
        path=virtual_path,
        virtual_path=virtual_path,
        artifact_url=_artifact_url(thread_id, virtual_path),
        extension=extension,
        modified=modified,
        mime_type=mime_type,
    )


def _unique_upload_target(thread_id: str, requested_filename: str) -> tuple[str, str, Path]:
    filename = _safe_upload_filename(requested_filename)
    virtual_path = _upload_virtual_path(filename)
    target = resolve_virtual_artifact_path(thread_id, virtual_path)
    if not target.exists():
        return filename, virtual_path, target

    stem = Path(filename).stem or "upload"
    suffix = Path(filename).suffix
    for _ in range(10):
        filename = f"{stem}-{uuid.uuid4().hex[:8]}{suffix}"
        virtual_path = _upload_virtual_path(filename)
        target = resolve_virtual_artifact_path(thread_id, virtual_path)
        if not target.exists():
            return filename, virtual_path, target
    raise HTTPException(status_code=409, detail="Could not allocate upload filename")


def _persist_upload(thread_id: str, upload: UploadFile, deps: ChatRouterDeps) -> UploadedFileInfo:
    filename, virtual_path, target = _unique_upload_target(thread_id, upload.filename or "upload")
    target.parent.mkdir(parents=True, exist_ok=True)

    size = 0
    try:
        with target.open("wb") as handle:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail=f"{filename} exceeds the 50 MB upload limit")
                handle.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise

    mime_type = upload.content_type or mimetypes.guess_type(filename)[0]
    deps.artifact_repo.create(
        conversation_id=thread_id,
        name=virtual_path,
        artifact_type="upload",
        path=virtual_path,
        mime_type=mime_type,
        size_bytes=size,
    )
    return _uploaded_file_info(thread_id, filename, virtual_path, size, mime_type)


def _strip_markdown_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
        return "\n".join(lines[1:-1]).strip()
    return stripped


def _parse_json_string_list(text: str) -> list[str] | None:
    candidate = _strip_markdown_code_fence(text)
    start = candidate.find("[")
    end = candidate.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        data = json.loads(candidate[start : end + 1])
    except Exception:
        return None
    if not isinstance(data, list):
        return None
    suggestions: list[str] = []
    for item in data:
        if isinstance(item, str) and item.strip():
            suggestions.append(item.strip())
    return suggestions


def _extract_response_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") in {"text", "output_text"}:
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts) if parts else ""
    if content is None:
        return ""
    return str(content)


def _format_suggestion_conversation(messages: list[SuggestionMessage]) -> str:
    parts: list[str] = []
    for message in messages:
        content = message.content.strip()
        if not content:
            continue
        role = message.role.strip().lower()
        if role in ("user", "human"):
            parts.append(f"User: {content}")
        elif role in ("assistant", "ai"):
            parts.append(f"Assistant: {content}")
        else:
            parts.append(f"{message.role}: {content}")
    return "\n".join(parts).strip()


def _create_suggestion_model(model_name: str | None):
    from deerflow.models import create_chat_model

    return create_chat_model(name=model_name, thinking_enabled=False)


async def _generate_followup_suggestions(thread_id: str, request: SuggestionsRequest) -> SuggestionsResponse:
    if not request.messages:
        return SuggestionsResponse(suggestions=[])

    conversation = _format_suggestion_conversation(request.messages)
    if not conversation:
        return SuggestionsResponse(suggestions=[])

    n = request.n
    system_instruction = (
        "You are generating follow-up questions to help the user continue the conversation.\n"
        f"Based on the conversation below, produce EXACTLY {n} short questions the user might ask next.\n"
        "Requirements:\n"
        "- Questions must be relevant to the preceding conversation.\n"
        "- Questions must be written in the same language as the user.\n"
        "- Keep each question concise (ideally <= 20 words / <= 40 Chinese characters).\n"
        "- Do NOT include numbering, markdown, or any extra text.\n"
        "- Output MUST be a JSON array of strings only.\n"
    )
    user_content = f"Conversation Context:\n{conversation}\n\nGenerate {n} follow-up questions"

    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        model = _create_suggestion_model(request.model_name)
        response = await model.ainvoke([SystemMessage(content=system_instruction), HumanMessage(content=user_content)])
        raw = _extract_response_text(response.content)
        suggestions = _parse_json_string_list(raw) or []
        cleaned = [item.replace("\n", " ").strip() for item in suggestions if item.strip()]
        return SuggestionsResponse(suggestions=cleaned[:n])
    except Exception as exc:
        logger.exception("Failed to generate suggestions: thread_id=%s err=%s", thread_id, exc)
        return SuggestionsResponse(suggestions=[])


def _message_type(message: ChatMessage) -> str | None:
    return message.type or ("human" if message.role == "user" else "ai" if message.role == "assistant" else message.role)


def _extract_text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts)
    return ""


def _message_text(message: ChatMessage) -> str:
    text = _extract_text_from_content(message.content)
    if text:
        return text
    for part in message.parts:
        if part.type == "text" and part.text:
            return part.text
    return ""


def _strip_uploaded_files_tag(content: str) -> str:
    return re.sub(r"\n*<uploaded_files>[\s\S]*?</uploaded_files>", "", content).strip()


def _native_human_message(message: ChatMessage, content: str) -> dict[str, Any]:
    """Build a DeerFlow/LangGraph human message payload from the request."""
    payload: dict[str, Any] = {
        "type": "human",
        "content": content,
        "additional_kwargs": message.additional_kwargs or {},
        "response_metadata": message.response_metadata or {},
    }
    if message.name is not None:
        payload["name"] = message.name
    return payload


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
            if _message_type(msg) == "human":
                last_user_text = _message_text(msg)
                if last_user_text:
                    break
        title_text = _strip_uploaded_files_tag(last_user_text)
        title = (title_text[:50] + "...") if len(title_text) > 50 else (title_text or "New Chat")
        conv = deps.conversation_repo.create(title=title, title_status="pending")
        conversation_id = conv.id

    if conversation_id is None:
        yield _serialize("error", {"code": "BAD_REQUEST", "message": "No conversation_id available"})
        return

    # Pull the latest user text from the request.
    user_text = ""
    user_message: ChatMessage | None = None
    for msg in reversed(body.messages):
        if _message_type(msg) == "human":
            user_text = _message_text(msg)
            if user_text:
                user_message = msg
                break

    if not user_text.strip():
        yield _serialize("error", {"code": "BAD_REQUEST", "message": "User message text is required"})
        return

    send_request = SendMessageRequest(
        content=user_text,
        mode=_parse_mode(body.mode),
        model_name=body.model_name,
        native_message=_native_human_message(user_message, user_text) if user_message is not None else None,
    )

    yield _serialize("conversation_start", {"conversation_id": conversation_id})

    try:
        if project_id:
            raw_stream = deps.stream_native_project_message(project_id, conversation_id, send_request)
        else:
            raw_stream = deps.stream_native_conversation_message(conversation_id, send_request)

        artifacts_emitted = False
        for raw_line in raw_stream:
            line = raw_line.strip() if isinstance(raw_line, str) else ""
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                event = None
            if isinstance(event, dict) and event.get("type") == "done":
                yield _serialize("artifacts", {"artifacts": _conversation_artifact_paths(deps, conversation_id)})
                artifacts_emitted = True
            yield raw_line if raw_line.endswith("\n") else f"{raw_line}\n"
        if not artifacts_emitted:
            yield _serialize("artifacts", {"artifacts": _conversation_artifact_paths(deps, conversation_id)})
    except HTTPException:
        raise
    except Exception as exc:
        yield _serialize("error", {"code": "STREAM_ERROR", "message": str(exc)})


def build_chat_router(deps: ChatRouterDeps) -> APIRouter:
    """Build the DeerFlow-native chat router."""
    router = APIRouter(prefix="/api")

    @router.post("/chat", tags=["chat"])
    def chat(body: ChatRequest) -> StreamingResponse:
        """Stream a chat turn as DeerFlow-native NDJSON events."""
        return StreamingResponse(
            _stream_chat(deps, body),
            media_type="application/x-ndjson",
        )

    @router.get("/chat/history", tags=["chat"])
    def chat_history(conversation_id: str) -> HistoryResponse:
        """Return persisted messages for a conversation as LangGraph Message array."""
        deps.conversation_repo.get_by_id(conversation_id)
        rows = deps.conversation_support.list_messages(conversation_id)
        return HistoryResponse(
            messages=_history_to_ui_messages(rows),
            conversation_id=conversation_id,
            artifacts=_conversation_artifact_paths(deps, conversation_id),
        )

    @router.post("/threads/{thread_id}/uploads", tags=["chat"])
    def upload_thread_files(thread_id: str, files: list[UploadFile] = File(...)) -> UploadResponse:
        """Upload files into a DeerFlow thread user-data directory."""
        deps.conversation_repo.get_by_id(thread_id)
        if not files:
            raise HTTPException(status_code=400, detail="No files uploaded")
        uploaded = [_persist_upload(thread_id, file, deps) for file in files]
        return UploadResponse(success=True, files=uploaded, message=f"Uploaded {len(uploaded)} file(s)")

    @router.get("/threads/{thread_id}/uploads/list", tags=["chat"])
    def list_thread_uploads(thread_id: str) -> ListUploadsResponse:
        """List files uploaded into a DeerFlow thread user-data directory."""
        deps.conversation_repo.get_by_id(thread_id)
        rows = [
            artifact
            for artifact in deps.artifact_repo.list_by_conversation(thread_id)
            if getattr(artifact, "artifact_type", None) == "upload"
        ]
        files = [
            _uploaded_file_info(
                thread_id,
                Path(artifact.path or artifact.name or "").name,
                artifact.path or artifact.name,
                int(artifact.size_bytes or 0),
                artifact.mime_type,
            )
            for artifact in rows
            if artifact.path or artifact.name
        ]
        return ListUploadsResponse(files=files, count=len(files))

    @router.post("/threads/{thread_id}/suggestions", tags=["chat"], response_model=SuggestionsResponse)
    async def thread_suggestions(thread_id: str, body: SuggestionsRequest) -> SuggestionsResponse:
        """Generate DeerFlow-native follow-up suggestions for the current thread."""
        deps.conversation_repo.get_by_id(thread_id)
        return await _generate_followup_suggestions(thread_id, body)

    @router.get(
        "/conversations/{conversation_id}/artifacts/{artifact_path:path}",
        tags=["chat"],
        responses={
            400: {"description": "Invalid artifact path"},
            403: {"description": "Artifact path escapes the conversation sandbox"},
            404: {"description": "Conversation or artifact not found"},
        },
    )
    def get_conversation_artifact_file(
        conversation_id: str,
        artifact_path: str,
        download: bool = False,
    ) -> Response:
        """Return a file from the conversation's DeerFlow user-data sandbox."""
        conversation = deps.conversation_repo.get_by_id(conversation_id)
        try:
            artifact = deps.artifact_repo.get_by_conversation_path(conversation_id, artifact_path)
            virtual_path = artifact.path or artifact.name or artifact_path
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
            normalized = normalize_virtual_path(artifact_path)
            if not normalized or not is_virtual_user_data_path(normalized):
                raise HTTPException(status_code=404, detail="Artifact not found") from None
            virtual_path = normalized
        thread_id = conversation.thread_id or conversation_id
        actual_path = resolve_virtual_artifact_path(thread_id, virtual_path)
        return build_artifact_file_response(actual_path, download=download)

    return router
