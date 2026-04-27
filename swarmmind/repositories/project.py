"""Project repository."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import ConversationDB, ProjectDB
from swarmmind.time_utils import utc_now


class ProjectRepository:
    """Repository for project operations."""

    def list_all(self) -> list[ProjectDB]:
        """List all projects ordered by updated_at descending."""
        with session_scope() as session:
            results = session.exec(
                select(ProjectDB).order_by(ProjectDB.updated_at.desc()),
            ).all()
            for r in results:
                session.expunge(r)
            return list(results)

    def get_by_id(self, project_id: str) -> ProjectDB:
        """Get a project by ID or raise 404."""
        with session_scope() as session:
            proj = session.get(ProjectDB, project_id)
            if proj is None:
                raise HTTPException(status_code=404, detail="Project not found")
            session.expunge(proj)
            return proj

    def create(
        self,
        *,
        title: str,
        goal: str | None = None,
        scope: str | None = None,
        constraints: str | None = None,
        source_conversation_id: str | None = None,
        next_step: str | None = None,
        phase: str | None = None,
        risk_level: str | None = None,
    ) -> ProjectDB:
        """Create a new project."""
        with session_scope() as session:
            proj = ProjectDB(
                project_id=str(uuid.uuid4()),
                title=title,
                goal=goal,
                scope=scope,
                constraints=constraints,
                source_conversation_id=source_conversation_id,
                next_step=next_step,
                phase=phase,
                risk_level=risk_level,
            )
            session.add(proj)
            session.commit()
            session.refresh(proj)
            session.expunge(proj)
            return proj

    def update(
        self,
        project_id: str,
        *,
        title: str | None = None,
        goal: str | None = None,
        scope: str | None = None,
        constraints: str | None = None,
        next_step: str | None = None,
        phase: str | None = None,
        risk_level: str | None = None,
        status: str | None = None,
    ) -> ProjectDB:
        """Update project fields."""
        with session_scope() as session:
            proj = session.get(ProjectDB, project_id)
            if proj is None:
                raise HTTPException(status_code=404, detail="Project not found")
            if title is not None:
                proj.title = title
            if goal is not None:
                proj.goal = goal
            if scope is not None:
                proj.scope = scope
            if constraints is not None:
                proj.constraints = constraints
            if next_step is not None:
                proj.next_step = next_step
            if phase is not None:
                proj.phase = phase
            if risk_level is not None:
                proj.risk_level = risk_level
            if status is not None:
                proj.status = status
            proj.updated_at = utc_now()
            session.commit()
            session.refresh(proj)
            session.expunge(proj)
            return proj

    def delete(self, project_id: str) -> None:
        """Delete a project by ID."""
        with session_scope() as session:
            proj = session.get(ProjectDB, project_id)
            if proj is not None:
                session.delete(proj)

    def link_conversation(self, project_id: str, conversation_id: str) -> None:
        """Link a conversation to a project via promoted_project_id."""
        with session_scope() as session:
            conv = session.get(ConversationDB, conversation_id)
            if conv is not None:
                conv.promoted_project_id = project_id
