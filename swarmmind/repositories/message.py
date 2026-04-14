"""Message repository."""

from __future__ import annotations

import uuid
from datetime import datetime

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
    ) -> MessageDB:
        """Create a new message.

        Note: tool_call_id and name are not yet persisted because the
        MessageDB model does not include those columns.
        """
        with session_scope() as session:
            msg = MessageDB(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                role=role,
                content=content,
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

    def create_clarification_response(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_call_id: str,
        name: str,
    ) -> dict:
        """Persist a clarification response with raw SQL for tool_call_id/name.

        This uses session-bound raw execution because MessageDB does not yet
        include tool_call_id and name columns.
        """
        from sqlalchemy import text

        message_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        with session_scope() as session:
            session.exec(
                text(
                    """
                    INSERT INTO messages (id, conversation_id, role, content, created_at, tool_call_id, name)
                    VALUES (:id, :conversation_id, :role, :content, :created_at, :tool_call_id, :name)
                    """,
                ),
                {
                    "id": message_id,
                    "conversation_id": conversation_id,
                    "role": role,
                    "content": content,
                    "created_at": now,
                    "tool_call_id": tool_call_id,
                    "name": name,
                },
            )
            return {
                "id": message_id,
                "role": role,
                "content": content,
                "tool_call_id": tool_call_id,
                "created_at": now,
            }
