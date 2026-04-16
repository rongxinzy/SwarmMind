"""Conversation title and message helper service."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from swarmmind.models import Conversation, Message
from swarmmind.repositories.conversation import ConversationRepository
from swarmmind.repositories.message import MessageRepository

logger = logging.getLogger(__name__)

NEW_CONVERSATION_TITLE = "New Conversation"


def _normalize_content(content: object) -> str:
    """Normalize possibly nested message content into plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [_normalize_content(item) for item in content]
        return "\n".join(part for part in parts if part)
    if isinstance(content, dict):
        text_value = content.get("text")
        if isinstance(text_value, str):
            return text_value
        nested = content.get("content")
        if nested is not None:
            return _normalize_content(nested)
    return ""


def generate_title_with_deerflow(user_msg: str, assistant_msg: str) -> tuple[str, str]:
    """Generate title in isolated session using deer-flow's capabilities."""
    try:
        from deerflow.config.title_config import get_title_config
        from deerflow.models import create_chat_model
    except ImportError:
        title = user_msg[:50] if len(user_msg) <= 50 else user_msg[:47] + "..."
        return title or NEW_CONVERSATION_TITLE, "fallback"

    config = get_title_config()
    user_normalized = _normalize_content(user_msg)[:500]
    assistant_normalized = _normalize_content(assistant_msg)[:500]
    prompt = config.prompt_template.format(
        max_words=config.max_words,
        user_msg=user_normalized,
        assistant_msg=assistant_normalized,
    )

    model = create_chat_model(name=config.model_name, thinking_enabled=False)

    try:
        response = model.invoke(prompt)
        title_content = _normalize_content(response.content).strip().strip('"').strip("'")
        title = title_content[: config.max_chars] if len(title_content) > config.max_chars else title_content
        if title:
            return title, "llm"
    except Exception:
        logger.exception("Title generation failed, using fallback")

    fallback_chars = min(config.max_chars, 50)
    if len(user_normalized) > fallback_chars:
        return user_normalized[:fallback_chars].rstrip() + "...", "fallback"
    return user_normalized or NEW_CONVERSATION_TITLE, "fallback"


class ConversationSupportService:
    """Lightweight support API for conversation/message helper responsibilities."""

    def __init__(
        self,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        title_generator: Callable[[str, str], tuple[str, str]] = generate_title_with_deerflow,
        new_conversation_title: str = NEW_CONVERSATION_TITLE,
    ) -> None:
        self._conversation_repo = conversation_repo
        self._message_repo = message_repo
        self._title_generator = title_generator
        self._new_conversation_title = new_conversation_title

    def db_to_conversation(self, conv: Any) -> Conversation:
        """Convert a conversation ORM row into the API model."""
        return Conversation(
            id=conv.id,
            title=conv.title,
            title_status=conv.title_status,
            title_source=conv.title_source,
            title_generated_at=(str(conv.title_generated_at) if conv.title_generated_at is not None else None),
            runtime_profile_id=(str(conv.runtime_profile_id) if conv.runtime_profile_id is not None else None),
            runtime_instance_id=(str(conv.runtime_instance_id) if conv.runtime_instance_id is not None else None),
            thread_id=str(conv.thread_id) if conv.thread_id is not None else None,
            promoted_project_id=str(conv.promoted_project_id) if conv.promoted_project_id is not None else None,
            created_at=str(conv.created_at) if conv.created_at is not None else "",
            updated_at=str(conv.updated_at) if conv.updated_at is not None else "",
        )

    def db_to_message(self, msg: Any) -> Message:
        """Convert a message ORM row into the API model."""
        return Message(
            id=msg.id,
            conversation_id=msg.conversation_id,
            role=msg.role,
            content=msg.content,
            tool_call_id=msg.tool_call_id,
            name=msg.name,
            run_id=msg.run_id,
            created_at=str(msg.created_at) if msg.created_at is not None else "",
        )

    def persist_user_message(self, conversation_id: str, content: str, run_id: str | None = None) -> Message:
        """Persist a user message and update the conversation timestamp."""
        self._conversation_repo.get_by_id(conversation_id)
        msg = self._message_repo.create(conversation_id, "user", content, run_id=run_id)
        self._conversation_repo.touch(conversation_id)
        return self.db_to_message(msg)

    def persist_assistant_message(self, conversation_id: str, content: str) -> Message:
        """Persist an assistant message and update the conversation timestamp."""
        msg = self._message_repo.create(conversation_id, "assistant", content)
        self._conversation_repo.touch(conversation_id)
        return self.db_to_message(msg)

    def maybe_generate_conversation_title(
        self,
        conversation_id: str,
        title_generator: Callable[[str, str], tuple[str, str]] | None = None,
    ) -> None:
        """Generate title after the first complete user+assistant exchange."""
        active_title_generator = title_generator or self._title_generator
        conversation = self._conversation_repo.get_by_id(conversation_id)
        if conversation.title_status != "pending":
            return

        messages = self._message_repo.list_by_conversation(conversation_id)
        user_messages = [msg.content for msg in messages if msg.role == "user"]
        assistant_messages = [msg.content for msg in messages if msg.role == "assistant"]

        if len(user_messages) != 1 or len(assistant_messages) < 1:
            return

        title, source = active_title_generator(user_messages[0], assistant_messages[0])
        self._conversation_repo.update_title(
            conversation_id,
            title or self._new_conversation_title,
            "generated" if source == "llm" else "fallback",
            source,
        )
