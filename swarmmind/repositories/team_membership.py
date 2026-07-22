"""Team membership repository."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import TeamMembershipDB
from swarmmind.time_utils import utc_now


class TeamMembershipRepository:
    """Repository for team membership operations."""

    def list_by_team(self, team_id: str) -> list[TeamMembershipDB]:
        """List memberships for a team."""
        with session_scope() as session:
            rows = session.exec(
                select(TeamMembershipDB)
                .where(TeamMembershipDB.team_id == team_id)
                .order_by(TeamMembershipDB.created_at.asc())
            ).all()
            for row in rows:
                session.expunge(row)
            return list(rows)

    def list_by_user(self, user_id: str) -> list[TeamMembershipDB]:
        """List team memberships for a user."""
        with session_scope() as session:
            rows = session.exec(
                select(TeamMembershipDB)
                .where(TeamMembershipDB.user_id == user_id)
                .order_by(TeamMembershipDB.created_at.asc())
            ).all()
            for row in rows:
                session.expunge(row)
            return list(rows)

    def get(self, membership_id: str) -> TeamMembershipDB:
        """Get a membership by ID or raise 404."""
        with session_scope() as session:
            row = session.get(TeamMembershipDB, membership_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Team membership not found")
            session.expunge(row)
            return row

    def create(
        self,
        *,
        team_id: str,
        user_id: str,
        role: str = "member",
        status: str = "active",
    ) -> TeamMembershipDB:
        """Add a user to a team."""
        with session_scope() as session:
            row = TeamMembershipDB(
                membership_id=str(uuid.uuid4()),
                team_id=team_id,
                user_id=user_id,
                role=role,
                status=status,
            )
            session.add(row)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise HTTPException(status_code=409, detail="User is already in this team") from exc
            session.refresh(row)
            session.expunge(row)
            return row

    def update(
        self,
        membership_id: str,
        *,
        role: str | None = None,
        status: str | None = None,
    ) -> TeamMembershipDB:
        """Update a team membership."""
        with session_scope() as session:
            row = session.get(TeamMembershipDB, membership_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Team membership not found")
            if role is not None:
                row.role = role
            if status is not None:
                row.status = status
            row.updated_at = utc_now()
            session.commit()
            session.refresh(row)
            session.expunge(row)
            return row

    def delete(self, membership_id: str) -> None:
        """Remove a user from a team."""
        with session_scope() as session:
            row = session.get(TeamMembershipDB, membership_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Team membership not found")
            session.delete(row)
            session.commit()
