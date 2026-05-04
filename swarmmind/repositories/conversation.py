"""Conversation repository."""

from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import HTTPException
from sqlmodel import delete, select

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

    def get_recent_active(self, since_days: int = 7) -> ConversationDB | None:
        """Get the most recent conversation that has messages within the given days."""
        from swarmmind.db_models import MessageDB

        with session_scope() as session:
            since = utc_now() - timedelta(days=since_days)
            result = session.exec(
                select(ConversationDB)
                .join(MessageDB, ConversationDB.id == MessageDB.conversation_id)
                .where(MessageDB.created_at >= since)
                .order_by(ConversationDB.updated_at.desc())
            ).first()
            if result is None:
                return None
            session.expunge(result)
            return result

    def get_next_after(self, deleted_id: str) -> ConversationDB | None:
        """Get the next most recently updated conversation after deleting the given one."""
        with session_scope() as session:
            result = session.exec(
                select(ConversationDB).where(ConversationDB.id != deleted_id).order_by(ConversationDB.updated_at.desc())
            ).first()
            if result is None:
                return None
            session.expunge(result)
            return result

    def delete(self, conversation_id: str) -> None:
        """Delete a conversation and its messages."""
        from swarmmind.db_models import MessageDB

        with session_scope() as session:
            # Explicitly delete messages first to avoid FK issues on SQLite
            session.exec(delete(MessageDB).where(MessageDB.conversation_id == conversation_id))
            conv = session.get(ConversationDB, conversation_id)
            if conv is not None:
                session.delete(conv)

    def search_by_query(self, q: str, limit: int = 20) -> list[ConversationDB]:
        """Search conversations by title or message content (case-insensitive)."""
        from sqlalchemy import func, or_

        from swarmmind.db_models import MessageDB

        q_lower = q.lower()
        pattern = f"%{q_lower}%"

        with session_scope() as session:
            msg_subquery = (
                select(MessageDB.conversation_id).where(func.lower(MessageDB.content).like(pattern)).distinct()
            )
            results = session.exec(
                select(ConversationDB)
                .where(
                    or_(
                        func.lower(ConversationDB.title).like(pattern),
                        ConversationDB.id.in_(msg_subquery),
                    )
                )
                .order_by(ConversationDB.updated_at.desc())
                .limit(limit)
            ).all()
            for r in results:
                session.expunge(r)
            return list(results)
