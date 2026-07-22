"""Team repository."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import TeamDB
from swarmmind.time_utils import utc_now


class TeamRepository:
    """Repository for team operations."""

    def list_by_organization(self, organization_id: str) -> list[TeamDB]:
        """List teams in an organization."""
        with session_scope() as session:
            rows = session.exec(
                select(TeamDB)
                .where(TeamDB.organization_id == organization_id)
                .order_by(TeamDB.created_at.asc())
            ).all()
            for row in rows:
                session.expunge(row)
            return list(rows)

    def get(self, team_id: str) -> TeamDB:
        """Get a team by ID or raise 404."""
        with session_scope() as session:
            row = session.get(TeamDB, team_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Team not found")
            session.expunge(row)
            return row

    def create(self, *, organization_id: str, name: str, status: str = "active") -> TeamDB:
        """Create a team in an organization."""
        with session_scope() as session:
            row = TeamDB(
                team_id=str(uuid.uuid4()),
                organization_id=organization_id,
                name=name,
                status=status,
            )
            session.add(row)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise HTTPException(status_code=409, detail="Team already exists or organization invalid") from exc
            session.refresh(row)
            session.expunge(row)
            return row

    def update(
        self,
        team_id: str,
        *,
        name: str | None = None,
        status: str | None = None,
    ) -> TeamDB:
        """Update a team."""
        with session_scope() as session:
            row = session.get(TeamDB, team_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Team not found")
            if name is not None:
                row.name = name
            if status is not None:
                row.status = status
            row.updated_at = utc_now()
            session.commit()
            session.refresh(row)
            session.expunge(row)
            return row

    def delete(self, team_id: str) -> None:
        """Archive a team."""
        with session_scope() as session:
            row = session.get(TeamDB, team_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Team not found")
            row.status = "archived"
            row.updated_at = utc_now()
            session.commit()
