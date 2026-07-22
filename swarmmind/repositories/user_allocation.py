"""User resource allocation repository."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import UserAllocationDB
from swarmmind.time_utils import utc_now


class UserAllocationRepository:
    """Repository for per-user resource allocations (models / MCP permissions)."""

    def list_by_user(self, user_id: str) -> list[UserAllocationDB]:
        """List all allocations for a user."""
        with session_scope() as session:
            rows = session.exec(
                select(UserAllocationDB)
                .where(UserAllocationDB.user_id == user_id)
                .order_by(UserAllocationDB.resource_type.asc(), UserAllocationDB.resource_name.asc())
            ).all()
            for row in rows:
                session.expunge(row)
            return list(rows)

    def get(self, allocation_id: str) -> UserAllocationDB:
        """Get an allocation by ID or raise 404."""
        with session_scope() as session:
            row = session.get(UserAllocationDB, allocation_id)
            if row is None:
                raise HTTPException(status_code=404, detail="User allocation not found")
            session.expunge(row)
            return row

    def set(
        self,
        *,
        user_id: str,
        resource_type: str,
        resource_name: str,
        is_allowed: int = 1,
    ) -> UserAllocationDB:
        """Create or update a user allocation."""
        with session_scope() as session:
            row = session.exec(
                select(UserAllocationDB)
                .where(UserAllocationDB.user_id == user_id)
                .where(UserAllocationDB.resource_type == resource_type)
                .where(UserAllocationDB.resource_name == resource_name)
            ).first()
            if row is None:
                row = UserAllocationDB(
                    allocation_id=str(uuid.uuid4()),
                    user_id=user_id,
                    resource_type=resource_type,
                    resource_name=resource_name,
                    is_allowed=is_allowed,
                )
                session.add(row)
            else:
                row.is_allowed = is_allowed
                row.updated_at = utc_now()
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise HTTPException(status_code=409, detail="User allocation conflict") from exc
            session.refresh(row)
            session.expunge(row)
            return row

    def delete(self, allocation_id: str) -> None:
        """Delete a user allocation."""
        with session_scope() as session:
            row = session.get(UserAllocationDB, allocation_id)
            if row is None:
                raise HTTPException(status_code=404, detail="User allocation not found")
            session.delete(row)
            session.commit()

    def delete_by_resource(
        self,
        *,
        user_id: str,
        resource_type: str,
        resource_name: str,
    ) -> None:
        """Delete a user allocation by user + resource."""
        with session_scope() as session:
            row = session.exec(
                select(UserAllocationDB)
                .where(UserAllocationDB.user_id == user_id)
                .where(UserAllocationDB.resource_type == resource_type)
                .where(UserAllocationDB.resource_name == resource_name)
            ).first()
            if row is not None:
                session.delete(row)
                session.commit()
