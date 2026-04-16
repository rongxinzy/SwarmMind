"""Message repository."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import MessageDB


class MessageRepository:
    """Repository for message operations."""

    def list_by_conversation(self, conversation_id: str) -> list[MessageDB]:
        """List messages for a conversation ordered by created_at ascending."""
        with session_scope() as session:
            results = session.exec(
                select(MessageDB)
                .where(MessageDB.conversation_id == conversation_id)
                .order_by(MessageDB.created_at.asc()),
            ).all()
            for r in results:
                session.expunge(r)
            return list(results)

    def create(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_call_id: str | None = None,
        name: str | None = None,
        run_id: str | None = None,
    ) -> MessageDB:
        """Create a new message."""
        with session_scope() as session:
            msg = MessageDB(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                role=role,
                content=content,
                tool_call_id=tool_call_id,
                name=name,
                run_id=run_id,
            )
            session.add(msg)
            session.commit()
            session.refresh(msg)
            session.expunge(msg)
            return msg

    def get_by_id(self, message_id: str) -> MessageDB:
        """Get a message by ID or raise 404."""
        with session_scope() as session:
            msg = session.get(MessageDB, message_id)
            if msg is None:
                raise HTTPException(status_code=404, detail="Message not found")
            session.expunge(msg)
            return msg
