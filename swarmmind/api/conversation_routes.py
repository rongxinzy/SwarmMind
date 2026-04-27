"""Conversation route registration helpers for the supervisor API."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import APIRouter, Query
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from swarmmind.models import (
    Conversation,
    ConversationListResponse,
    ConversationTraceResponse,
    CreateConversationRequest,
    DeleteConversationResponse,
    Message,
    MessageListResponse,
    RecentConversationResponse,
    SendMessageRequest,
)


class ClarificationResponseRequest(BaseModel):
    """Request to respond to a clarification prompt."""

    tool_call_id: str
    response: str


@dataclass(frozen=True)
class ConversationRouteHandlers:
    """Direct-call handlers re-exported by supervisor for compatibility."""

    list_conversations: Callable[[], ConversationListResponse]
    create_conversation: Callable[[GoalRequest], Conversation]
    get_conversation: Callable[..., Conversation]
    get_recent_conversation: Callable[[], RecentConversationResponse | None]
    get_conversation_messages: Callable[[str], MessageListResponse]
    send_message: Callable[[str, SendMessageRequest], object]
    delete_conversation: Callable[[str], DeleteConversationResponse]
    get_conversation_trace: Callable[[str], dict]
    stream_conversation_message: Callable[[str, SendMessageRequest], object]
    send_message_stream: Callable[[str, SendMessageRequest], StreamingResponse]
    respond_to_clarification: Callable[[str, ClarificationResponseRequest], Message]


@dataclass(frozen=True)
class ConversationRouteDeps:
    """Injected dependencies for the conversation router."""

    list_conversations: Callable[[], ConversationListResponse]
    create_conversation: Callable[[CreateConversationRequest], Conversation]
    get_conversation: Callable[..., Conversation]
    get_recent_conversation: Callable[[], RecentConversationResponse | None]
    get_conversation_messages: Callable[[str], MessageListResponse]
    send_message: Callable[[str, SendMessageRequest], object]
    delete_conversation: Callable[[str], DeleteConversationResponse]
    get_conversation_trace: Callable[[str], ConversationTraceResponse]
    stream_conversation_message: Callable[[str, SendMessageRequest], object]
    respond_to_clarification: Callable[[str, str, str], Message]


def build_conversation_router(*, deps: ConversationRouteDeps) -> tuple[APIRouter, ConversationRouteHandlers]:
    """Build the conversation router from injected supervisor dependencies."""
    router = APIRouter()

    @router.get("/conversations", tags=["conversations"])
    def list_conversations() -> ConversationListResponse:
        """List all conversations ordered by updated_at descending."""
        return deps.list_conversations()

    @router.post("/conversations", tags=["conversations"])
    def create_conversation(body: CreateConversationRequest) -> Conversation:
        """Create a new conversation."""
        return deps.create_conversation(body)

    @router.get("/conversations/recent", tags=["conversations"])
    def get_recent_conversation() -> RecentConversationResponse:
        """Get the most recent active conversation (within 7 days) with its messages."""
        result = deps.get_recent_conversation()
        if result is None:
            return Response(status_code=204)
        return result

    @router.get("/conversations/{conversation_id}", tags=["conversations"], responses={404: {"description": "Conversation not found"}})
    def get_conversation(
        conversation_id: str,
        include_messages: bool = Query(False),
    ) -> Conversation:
        """Get a single conversation by ID."""
        return deps.get_conversation(conversation_id, include_messages=include_messages)

    @router.get("/conversations/{conversation_id}/messages", tags=["conversations"], responses={404: {"description": "Conversation not found"}})
    def get_conversation_messages(conversation_id: str) -> MessageListResponse:
        """Get all messages for a conversation."""
        return deps.get_conversation_messages(conversation_id)

    @router.post("/conversations/{conversation_id}/messages", include_in_schema=False)
    def send_message(conversation_id: str, body: SendMessageRequest):
        """Internal compatibility endpoint for non-streaming conversation turns."""
        return deps.send_message(conversation_id, body)

    @router.delete("/conversations/{conversation_id}", tags=["conversations"], responses={404: {"description": "Conversation not found"}})
    def delete_conversation(conversation_id: str) -> DeleteConversationResponse:
        """Delete a conversation and all its messages."""
        return deps.delete_conversation(conversation_id)

    @router.get("/conversations/{conversation_id}/trace", tags=["conversations"], responses={404: {"description": "Conversation not found"}})
    def get_conversation_trace(conversation_id: str) -> ConversationTraceResponse:
        """Return the collaboration trace for a conversation."""
        return deps.get_conversation_trace(conversation_id)

    def _stream_conversation_message(conversation_id: str, body: SendMessageRequest):
        """Stream a ChatSession turn with SwarmMind runtime semantics."""
        yield from deps.stream_conversation_message(conversation_id, body)

    @router.post("/conversations/{conversation_id}/messages/stream", tags=["conversations"], responses={404: {"description": "Conversation not found"}})
    def send_message_stream(conversation_id: str, body: SendMessageRequest) -> StreamingResponse:
        """Stream a ChatSession turn with runtime state and final persistence."""
        get_conversation(conversation_id)
        return StreamingResponse(
            _stream_conversation_message(conversation_id, body),
            media_type="application/x-ndjson",
        )

    @router.post("/conversations/{conversation_id}/clarification", tags=["conversations"], responses={404: {"description": "Conversation not found"}})
    def respond_to_clarification(conversation_id: str, body: ClarificationResponseRequest) -> Message:
        """Resume the conversation from a clarification response."""
        return deps.respond_to_clarification(
            conversation_id,
            body.tool_call_id,
            body.response,
        )

    return router, ConversationRouteHandlers(
        list_conversations=list_conversations,
        create_conversation=create_conversation,
        get_conversation=get_conversation,
        get_recent_conversation=get_recent_conversation,
        get_conversation_messages=get_conversation_messages,
        send_message=send_message,
        delete_conversation=delete_conversation,
        get_conversation_trace=get_conversation_trace,
        stream_conversation_message=_stream_conversation_message,
        send_message_stream=send_message_stream,
        respond_to_clarification=respond_to_clarification,
    )
