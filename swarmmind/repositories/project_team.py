"""Project agent team instance repository."""

from __future__ import annotations

import json
import uuid

from fastapi import HTTPException
from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import ProjectAgentTeamInstanceDB
from swarmmind.time_utils import utc_now


class ProjectTeamInstanceRepository:
    """Repository for project agent team instance operations."""

    def get_by_project(self, project_id: str) -> ProjectAgentTeamInstanceDB | None:
        """Get the team instance for a project, or None if not attached."""
        with session_scope() as session:
            result = session.exec(
                select(ProjectAgentTeamInstanceDB).where(ProjectAgentTeamInstanceDB.project_id == project_id),
            ).first()
            if result is not None:
                session.expunge(result)
            return result

    def create(
        self,
        *,
        project_id: str,
        team_template_id: str,
        instance_config: dict | None = None,
    ) -> ProjectAgentTeamInstanceDB:
        """Attach a team template to a project."""
        with session_scope() as session:
            # Check if project already has a team instance
            existing = session.exec(
                select(ProjectAgentTeamInstanceDB).where(ProjectAgentTeamInstanceDB.project_id == project_id),
            ).first()
            if existing is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Project already has an agent team attached",
                )

            instance = ProjectAgentTeamInstanceDB(
                instance_id=str(uuid.uuid4()),
                project_id=project_id,
                team_template_id=team_template_id,
                instance_config=json.dumps(instance_config or {}),
                status="active",
            )
            session.add(instance)
            session.commit()
            session.refresh(instance)
            session.expunge(instance)
            return instance

    def update(
        self,
        project_id: str,
        *,
        instance_config: dict | None = None,
        status: str | None = None,
    ) -> ProjectAgentTeamInstanceDB:
        """Update a project team instance."""
        with session_scope() as session:
            instance = session.exec(
                select(ProjectAgentTeamInstanceDB).where(ProjectAgentTeamInstanceDB.project_id == project_id),
            ).first()
            if instance is None:
                raise HTTPException(
                    status_code=404,
                    detail="Project does not have an agent team attached",
                )
            if instance_config is not None:
                instance.instance_config = json.dumps(instance_config)
            if status is not None:
                instance.status = status
            instance.updated_at = utc_now()
            session.commit()
            session.refresh(instance)
            session.expunge(instance)
            return instance

    def delete(self, project_id: str) -> bool:
        """Detach the team from a project."""
        with session_scope() as session:
            instance = session.exec(
                select(ProjectAgentTeamInstanceDB).where(ProjectAgentTeamInstanceDB.project_id == project_id),
            ).first()
            if instance is None:
                return False
            session.delete(instance)
            session.commit()
            return True
