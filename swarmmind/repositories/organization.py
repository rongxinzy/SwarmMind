"""Organization repository."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import OrganizationDB
from swarmmind.time_utils import utc_now


class OrganizationRepository:
    """Repository for organization operations."""

    def list_all(self) -> list[OrganizationDB]:
        """List all organizations ordered by creation time."""
        with session_scope() as session:
            rows = session.exec(select(OrganizationDB).order_by(OrganizationDB.created_at.asc())).all()
            for row in rows:
                session.expunge(row)
            return list(rows)

    def get(self, organization_id: str) -> OrganizationDB:
        """Get an organization by ID or raise 404."""
        with session_scope() as session:
            row = session.get(OrganizationDB, organization_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Organization not found")
            session.expunge(row)
            return row

    def create(self, *, name: str, owner_user_id: str, status: str = "active") -> OrganizationDB:
        """Create an organization."""
        with session_scope() as session:
            row = OrganizationDB(
                organization_id=str(uuid.uuid4()),
                name=name,
                owner_user_id=owner_user_id,
                status=status,
            )
            session.add(row)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise HTTPException(status_code=409, detail="Organization owner does not exist") from exc
            session.refresh(row)
            session.expunge(row)
            return row

    def update(
        self,
        organization_id: str,
        *,
        name: str | None = None,
        owner_user_id: str | None = None,
        status: str | None = None,
    ) -> OrganizationDB:
        """Update an organization."""
        with session_scope() as session:
            row = session.get(OrganizationDB, organization_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Organization not found")
            if name is not None:
                row.name = name
            if owner_user_id is not None:
                row.owner_user_id = owner_user_id
            if status is not None:
                row.status = status
            row.updated_at = utc_now()
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise HTTPException(status_code=409, detail="Organization owner does not exist") from exc
            session.refresh(row)
            session.expunge(row)
            return row

    def delete(self, organization_id: str) -> None:
        """Archive an organization."""
        with session_scope() as session:
            row = session.get(OrganizationDB, organization_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Organization not found")
            row.status = "archived"
            row.updated_at = utc_now()
            session.commit()
