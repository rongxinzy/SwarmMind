"""Agent team template domain routes."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter

from swarmmind.api.routers.mappers import db_to_team_template
from swarmmind.models import (
    AgentTeamTemplate,
    AgentTeamTemplateCreateRequest,
    AgentTeamTemplateListResponse,
    AgentTeamTemplateUpdateRequest,
)


@dataclass(frozen=True)
class AgentTeamsRouterDeps:
    agent_team_repo: object


def build_agent_teams_router(deps: AgentTeamsRouterDeps) -> APIRouter:
    router = APIRouter()

    @router.get("/agent-teams", tags=["agent-teams"])
    def list_agent_teams() -> AgentTeamTemplateListResponse:
        """List all enabled agent team templates."""
        rows = deps.agent_team_repo.list_all(include_disabled=False)
        return AgentTeamTemplateListResponse(items=[db_to_team_template(r) for r in rows], total=len(rows))

    @router.get("/agent-teams/{team_id}", tags=["agent-teams"], responses={404: {"description": "Team template not found"}})
    def get_agent_team(team_id: str) -> AgentTeamTemplate:
        """Get a single agent team template by ID."""
        return db_to_team_template(deps.agent_team_repo.get_by_id(team_id))

    @router.post("/agent-teams", tags=["agent-teams"], status_code=201)
    def create_agent_team(body: AgentTeamTemplateCreateRequest) -> AgentTeamTemplate:
        """Create a new custom agent team template."""
        team = deps.agent_team_repo.create(
            name=body.name,
            description=body.description,
            icon=body.icon,
            roles=[r.model_dump() for r in body.roles],
            default_skills=body.default_skills,
            runtime_profile_prefs=body.runtime_profile_prefs,
            is_builtin=False,
        )
        return db_to_team_template(team)

    @router.patch("/agent-teams/{team_id}", tags=["agent-teams"], responses={404: {"description": "Team template not found"}})
    def update_agent_team(team_id: str, body: AgentTeamTemplateUpdateRequest) -> AgentTeamTemplate:
        """Update an agent team template."""
        roles = [r.model_dump() for r in body.roles] if body.roles is not None else None
        team = deps.agent_team_repo.update(
            team_id=team_id,
            name=body.name,
            description=body.description,
            icon=body.icon,
            roles=roles,
            default_skills=body.default_skills,
            runtime_profile_prefs=body.runtime_profile_prefs,
            is_enabled=body.is_enabled,
        )
        return db_to_team_template(team)

    @router.delete("/agent-teams/{team_id}", tags=["agent-teams"], status_code=204)
    def delete_agent_team(team_id: str) -> None:
        """Disable an agent team template."""
        deps.agent_team_repo.delete(team_id)

    return router
