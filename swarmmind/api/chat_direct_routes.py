"""Direct Chat mode routes.

Chat mode is a thin, Vercel AI SDK-backed conversation surface. It connects
the frontend directly to the SwarmMind LLM Gateway using a backend-issued key
and model list. Messages are persisted in SwarmMind so the conversation list
and history remain owned by the backend.

Endpoints:
- GET  /chat/models           : models + gateway credentials for Chat mode.
- POST /chat/conversations    : create a new Chat conversation.
- GET  /chat/conversations    : list Chat conversations.
- GET  /chat/conversations/{id}/messages : list persisted messages.
- POST /chat/conversations/{id}/messages : persist user/assistant messages.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from swarmmind.models import (
    ChatModelInfo,
    ChatModelListResponse,
    ChatTurnRequest,
    Conversation,
    ConversationListResponse,
    MessageListResponse,
    SessionType,
)
from swarmmind.repositories.conversation import ConversationRepository
from swarmmind.repositories.message import MessageRepository
from swarmmind.runtime.catalog import (
    ANONYMOUS_SUBJECT_ID,
    ANONYMOUS_SUBJECT_TYPE,
    list_models_for_subject,
)
from swarmmind.services.conversation_support import ConversationSupportService
from swarmmind.services.gateway_key import get_gateway_base_url, get_gateway_key

logger = logging.getLogger(__name__)

DEFAULT_CHAT_TITLE = "New Chat"


class ChatDirectRouterDeps:
    """Dependencies for the direct Chat router."""

    def __init__(
        self,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        conversation_support: ConversationSupportService,
    ) -> None:
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo
        self.conversation_support = conversation_support


def build_chat_direct_router(deps: ChatDirectRouterDeps) -> APIRouter:
    """Build the direct Chat mode router."""
    router = APIRouter(prefix="/chat")

    @router.get("/models", response_model=ChatModelListResponse, tags=["chat-direct"])
    def list_chat_models() -> ChatModelListResponse:
        """Return models available for direct Chat mode plus gateway credentials."""
        base_url = get_gateway_base_url()
        api_key = get_gateway_key()
        runtime_models = list_models_for_subject(ANONYMOUS_SUBJECT_TYPE, ANONYMOUS_SUBJECT_ID)

        models: list[ChatModelInfo] = []
        default_model: str | None = None
        for rm in runtime_models:
            info = ChatModelInfo(
                id=rm.name,
                name=rm.name,
                provider=rm.provider,
                model=rm.model,
                display_name=rm.display_name or rm.name,
                description=rm.description,
                supports_vision=rm.supports_vision,
                supports_thinking=rm.supports_thinking,
                base_url=base_url,
                api_key=api_key,
                is_default=rm.is_default,
            )
            models.append(info)
            if rm.is_default:
                default_model = rm.name

        if not models:
            return ChatModelListResponse(models=[], default_model=None)

        if default_model is None:
            default_model = models[0].id

        return ChatModelListResponse(models=models, default_model=default_model)

    @router.post("/conversations", response_model=Conversation, tags=["chat-direct"])
    def create_chat_conversation() -> Conversation:
        """Create a new direct Chat conversation."""
        conv = deps.conversation_repo.create(
            title=DEFAULT_CHAT_TITLE,
            title_status="pending",
            session_type=SessionType.CHAT.value,
        )
        return deps.conversation_support.db_to_conversation(conv)

    @router.get("/conversations", response_model=ConversationListResponse, tags=["chat-direct"])
    def list_chat_conversations() -> ConversationListResponse:
        """List direct Chat conversations ordered by updated_at descending."""
        rows = deps.conversation_repo.list_by_session_type(SessionType.CHAT.value)
        items = [deps.conversation_support.db_to_conversation(r) for r in rows]
        return ConversationListResponse(items=items, total=len(items))

    @router.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse, tags=["chat-direct"])
    def list_chat_messages(conversation_id: str) -> MessageListResponse:
        """List persisted messages for a Chat conversation."""
        deps.conversation_repo.get_by_id(conversation_id)
        rows = deps.message_repo.list_by_conversation(conversation_id)
        items = [deps.conversation_support.db_to_message(m) for m in rows]
        return MessageListResponse(items=items, total=len(items))

    @router.post("/conversations/{conversation_id}/messages", tags=["chat-direct"])
    def persist_chat_messages(conversation_id: str, body: ChatTurnRequest) -> dict[str, Any]:
        """Persist one or more Chat messages and update the conversation timestamp."""
        deps.conversation_repo.get_by_id(conversation_id)

        persisted: list[Any] = []
        for msg in body.messages:
            if msg.role not in ("user", "assistant"):
                raise HTTPException(status_code=400, detail=f"Invalid role: {msg.role}")
            row = deps.message_repo.create(conversation_id, msg.role, msg.content)
            persisted.append(deps.conversation_support.db_to_message(row))

        deps.conversation_repo.touch(conversation_id)

        # Generate a title on the first complete user+assistant exchange.
        if len(body.messages) >= 2:
            deps.conversation_support.maybe_generate_conversation_title(conversation_id)

        return {"messages": persisted}

    return router
