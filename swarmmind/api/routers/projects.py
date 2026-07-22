"""Project domain routes: CRUD only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Query

from swarmmind.api.routers.mappers import db_to_project
from swarmmind.models import (
    DeleteProjectResponse,
    Project,
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectUpdateRequest,
)


@dataclass(frozen=True)
class ProjectsRouterDeps:
    """Dependencies for the projects router."""

    project_repo: object


def build_projects_router(deps: ProjectsRouterDeps) -> APIRouter:
    """Return an APIRouter with project CRUD endpoints."""
    router = APIRouter()

    @router.get("/projects", tags=["projects"])
    def list_projects(
        limit: Annotated[int | None, Query(ge=1, le=500)] = None,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> ProjectListResponse:
        """List all projects ordered by updated_at descending."""
        rows = deps.project_repo.list_all(limit=limit, offset=offset)
        return ProjectListResponse(items=[db_to_project(r) for r in rows], total=deps.project_repo.count_all())

    @router.get("/projects/{project_id}", tags=["projects"], responses={404: {"description": "Project not found"}})
    def get_project(project_id: str) -> Project:
        """Get a single project by ID."""
        return db_to_project(deps.project_repo.get_by_id(project_id))

    @router.post("/projects", tags=["projects"])
    def create_project(body: ProjectCreateRequest) -> Project:
        """Create a new project manually."""
        proj = deps.project_repo.create(
            title=body.title,
            goal=body.goal,
            scope=body.scope,
            constraints=body.constraints,
            next_step=body.next_step,
            phase=body.phase,
            risk_level=body.risk_level,
        )
        return db_to_project(proj)

    @router.delete("/projects/{project_id}", tags=["projects"], responses={404: {"description": "Project not found"}})
    def delete_project(project_id: str) -> DeleteProjectResponse:
        """Delete a project."""
        deps.project_repo.get_by_id(project_id)
        deps.project_repo.delete(project_id)
        return DeleteProjectResponse(project_id=project_id)

    @router.patch("/projects/{project_id}", tags=["projects"], responses={404: {"description": "Project not found"}})
    def update_project(project_id: str, body: ProjectUpdateRequest) -> Project:
        """Update a project. Only provided fields are changed."""
        fields: dict[str, object] = {}
        if body.title is not None:
            fields["title"] = body.title
        if body.goal is not None:
            fields["goal"] = body.goal
        if body.scope is not None:
            fields["scope"] = body.scope
        if body.constraints is not None:
            fields["constraints"] = body.constraints
        if body.next_step is not None:
            fields["next_step"] = body.next_step
        if body.phase is not None:
            fields["phase"] = body.phase
        if body.risk_level is not None:
            fields["risk_level"] = body.risk_level
        if body.status is not None:
            fields["status"] = body.status.value
        if not fields:
            return db_to_project(deps.project_repo.get_by_id(project_id))
        deps.project_repo.update(project_id, **fields)
        return db_to_project(deps.project_repo.get_by_id(project_id))

    return router
