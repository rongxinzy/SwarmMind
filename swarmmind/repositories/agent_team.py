"""Agent team template repository."""

from __future__ import annotations

import json
import uuid

from fastapi import HTTPException
from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import AgentTeamTemplateDB
from swarmmind.time_utils import utc_now


class AgentTeamRepository:
    """Repository for agent team template operations."""

    def list_all(self, include_disabled: bool = False) -> list[AgentTeamTemplateDB]:
        """List all agent team templates ordered by created_at descending."""
        with session_scope() as session:
            query = select(AgentTeamTemplateDB).order_by(AgentTeamTemplateDB.created_at.desc())
            if not include_disabled:
                query = query.where(AgentTeamTemplateDB.is_enabled == 1)
            results = session.exec(query).all()
            for r in results:
                session.expunge(r)
            return list(results)

    def get_by_id(self, team_id: str) -> AgentTeamTemplateDB:
        """Get a team template by ID or raise 404."""
        with session_scope() as session:
            team = session.get(AgentTeamTemplateDB, team_id)
            if team is None:
                raise HTTPException(status_code=404, detail="Agent team template not found")
            session.expunge(team)
            return team

    def create(
        self,
        *,
        name: str,
        description: str | None = None,
        icon: str | None = None,
        roles: list[dict] | None = None,
        default_skills: list[str] | None = None,
        runtime_profile_prefs: dict | None = None,
        is_builtin: bool = False,
    ) -> AgentTeamTemplateDB:
        """Create a new agent team template."""
        with session_scope() as session:
            team = AgentTeamTemplateDB(
                team_id=str(uuid.uuid4()),
                name=name,
                description=description,
                icon=icon,
                roles=json.dumps(roles or []),
                default_skills=json.dumps(default_skills or []),
                runtime_profile_prefs=json.dumps(runtime_profile_prefs or {}),
                is_builtin=1 if is_builtin else 0,
            )
            session.add(team)
            session.commit()
            session.refresh(team)
            session.expunge(team)
            return team

    def update(
        self,
        team_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        icon: str | None = None,
        roles: list[dict] | None = None,
        default_skills: list[str] | None = None,
        runtime_profile_prefs: dict | None = None,
        is_enabled: bool | None = None,
    ) -> AgentTeamTemplateDB:
        """Update a team template. Only provided fields are changed."""
        with session_scope() as session:
            team = session.get(AgentTeamTemplateDB, team_id)
            if team is None:
                raise HTTPException(status_code=404, detail="Agent team template not found")
            if name is not None:
                team.name = name
            if description is not None:
                team.description = description
            if icon is not None:
                team.icon = icon
            if roles is not None:
                team.roles = json.dumps(roles)
            if default_skills is not None:
                team.default_skills = json.dumps(default_skills)
            if runtime_profile_prefs is not None:
                team.runtime_profile_prefs = json.dumps(runtime_profile_prefs)
            if is_enabled is not None:
                team.is_enabled = 1 if is_enabled else 0
            team.updated_at = utc_now()
            session.commit()
            session.refresh(team)
            session.expunge(team)
            return team

    def delete(self, team_id: str) -> bool:
        """Disable a team template (soft delete)."""
        with session_scope() as session:
            team = session.get(AgentTeamTemplateDB, team_id)
            if team is None:
                return False
            team.is_enabled = 0
            team.updated_at = utc_now()
            session.commit()
            return True
