"""Conversation repository."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import ConversationDB
from swarmmind.time_utils import utc_now


class ConversationRepository:
    """Repository for conversation operations."""

    def list_all(self) -> list[ConversationDB]:
        """List all conversations ordered by updated_at descending."""
        with session_scope() as session:
            results = session.exec(
                select(ConversationDB).order_by(ConversationDB.updated_at.desc()),
            ).all()
            for r in results:
                session.expunge(r)
            return list(results)

    def get_by_id(self, conversation_id: str) -> ConversationDB:
        """Get a conversation by ID or raise 404."""
        with session_scope() as session:
            conv = session.get(ConversationDB, conversation_id)
            if conv is None:
                raise HTTPException(status_code=404, detail="Conversation not found")
            session.expunge(conv)
            return conv

    def create(self, title: str, title_status: str) -> ConversationDB:
        """Create a new conversation."""
        with session_scope() as session:
            conv = ConversationDB(
                id=str(uuid.uuid4()),
                title=title,
                title_status=title_status,
            )
            session.add(conv)
            session.commit()
            session.refresh(conv)
            session.expunge(conv)
            return conv

    def update_runtime(
        self,
        conversation_id: str,
        runtime_profile_id: str | None,
        runtime_instance_id: str | None,
        thread_id: str | None,
    ) -> None:
        """Bind runtime metadata to a conversation."""
        with session_scope() as session:
            conv = session.get(ConversationDB, conversation_id)
            if conv is not None:
                conv.runtime_profile_id = runtime_profile_id
                conv.runtime_instance_id = runtime_instance_id
                conv.thread_id = thread_id

    def update_title(
        self,
        conversation_id: str,
        title: str,
        title_status: str,
        title_source: str | None,
    ) -> None:
        """Update conversation title metadata."""
        with session_scope() as session:
            conv = session.get(ConversationDB, conversation_id)
            if conv is not None:
                conv.title = title
                conv.title_status = title_status
                conv.title_source = title_source
                conv.title_generated_at = utc_now()

    def touch(self, conversation_id: str) -> None:
        """Bump updated_at for a conversation."""
        with session_scope() as session:
            conv = session.get(ConversationDB, conversation_id)
            if conv is not None:
                conv.updated_at = utc_now()

    def delete(self, conversation_id: str) -> None:
        """Delete a conversation and its messages (cascade via FK)."""
        with session_scope() as session:
            conv = session.get(ConversationDB, conversation_id)
            if conv is not None:
                session.delete(conv)
