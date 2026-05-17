"""Project membership repository."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import ProjectMembershipDB
from swarmmind.time_utils import utc_now


class ProjectMembershipRepository:
    """Repository for minimal project membership/RBAC operations."""

    def list_by_project(self, project_id: str) -> list[ProjectMembershipDB]:
        """List active and inactive members for a project."""
        with session_scope() as session:
            rows = session.exec(
                select(ProjectMembershipDB)
                .where(ProjectMembershipDB.project_id == project_id)
                .order_by(ProjectMembershipDB.created_at.asc())
            ).all()
            for row in rows:
                session.expunge(row)
            return list(rows)

    def get(self, membership_id: str) -> ProjectMembershipDB:
        """Get a membership by ID or raise 404."""
        with session_scope() as session:
            row = session.get(ProjectMembershipDB, membership_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Project membership not found")
            session.expunge(row)
            return row

    def get_by_member(self, project_id: str, member_id: str) -> ProjectMembershipDB:
        """Get a project membership by project and member ID or raise 404."""
        with session_scope() as session:
            row = session.exec(
                select(ProjectMembershipDB)
                .where(ProjectMembershipDB.project_id == project_id)
                .where(ProjectMembershipDB.member_id == member_id)
            ).first()
            if row is None:
                raise HTTPException(status_code=404, detail="Project membership not found")
            session.expunge(row)
            return row

    def create(
        self,
        *,
        project_id: str,
        member_id: str,
        display_name: str | None = None,
        role: str = "viewer",
        status: str = "active",
    ) -> ProjectMembershipDB:
        """Create a project membership."""
        with session_scope() as session:
            row = ProjectMembershipDB(
                membership_id=str(uuid.uuid4()),
                project_id=project_id,
                member_id=member_id,
                display_name=display_name,
                role=role,
                status=status,
            )
            session.add(row)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise HTTPException(status_code=409, detail="Project member already exists") from exc
            session.refresh(row)
            session.expunge(row)
            return row

    def update(
        self,
        membership_id: str,
        *,
        display_name: str | None = None,
        role: str | None = None,
        status: str | None = None,
    ) -> ProjectMembershipDB:
        """Update a project membership."""
        with session_scope() as session:
            row = session.get(ProjectMembershipDB, membership_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Project membership not found")
            if display_name is not None:
                row.display_name = display_name
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
        """Delete a project membership."""
        with session_scope() as session:
            row = session.get(ProjectMembershipDB, membership_id)
            if row is not None:
                session.delete(row)
