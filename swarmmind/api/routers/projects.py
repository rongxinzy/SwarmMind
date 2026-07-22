"""Project domain routes: CRUD plus workspace endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Query

from swarmmind.api.routers.mappers import db_to_project, db_to_project_memory
from swarmmind.models import (
    Conversation,
    ConversationListResponse,
    DeleteProjectResponse,
    Project,
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectMemoryEntry,
    ProjectMemoryListResponse,
    ProjectMemorySetRequest,
    ProjectUpdateRequest,
)
from swarmmind.services.conversation_support import ConversationSupportService


@dataclass(frozen=True)
class ProjectsRouterDeps:
    """Dependencies for the projects router."""

    project_repo: object
    conversation_repo: object
    conversation_support: ConversationSupportService
    memory_repo: object
    artifact_repo: object


def build_projects_router(deps: ProjectsRouterDeps) -> APIRouter:
    """Return an APIRouter with project CRUD and workspace endpoints."""
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

    # ---- Workspace endpoints ----

    @router.get(
        "/projects/{project_id}/conversations",
        tags=["projects"],
        responses={404: {"description": "Project not found"}},
    )
    def list_project_conversations(project_id: str) -> ConversationListResponse:
        """List task sessions belonging to a project."""
        deps.project_repo.get_by_id(project_id)
        rows = deps.conversation_repo.list_by_project(project_id)
        items = [deps.conversation_support.db_to_conversation(r) for r in rows]
        return ConversationListResponse(items=items, total=len(items))

    @router.post(
        "/projects/{project_id}/conversations",
        tags=["projects"],
        responses={404: {"description": "Project not found"}},
    )
    def create_project_conversation(project_id: str) -> Conversation:
        """Create a new task session inside a project."""
        deps.project_repo.get_by_id(project_id)
        conv = deps.conversation_repo.create(
            title="New Task",
            title_status="pending",
            session_type="task",
            project_id=project_id,
        )
        deps.conversation_repo.mark_project_bound(conv.id)
        return deps.conversation_support.db_to_conversation(conv)

    @router.get(
        "/projects/{project_id}/memory",
        tags=["projects"],
        responses={404: {"description": "Project not found"}},
    )
    def list_project_memory(project_id: str) -> ProjectMemoryListResponse:
        """List shared memory entries for a project."""
        deps.project_repo.get_by_id(project_id)
        rows = deps.memory_repo.list_by_project(project_id)
        items = [db_to_project_memory(r) for r in rows]
        return ProjectMemoryListResponse(items=items, total=len(items))

    @router.put(
        "/projects/{project_id}/memory/{key}",
        tags=["projects"],
        responses={404: {"description": "Project not found"}},
    )
    def set_project_memory(project_id: str, key: str, body: ProjectMemorySetRequest) -> ProjectMemoryEntry:
        """Set a shared memory entry for a project."""
        deps.project_repo.get_by_id(project_id)
        entry = deps.memory_repo.set(project_id, key, body.value)
        return db_to_project_memory(entry)

    @router.delete(
        "/projects/{project_id}/memory/{key}",
        tags=["projects"],
        responses={404: {"description": "Project or memory entry not found"}},
    )
    def delete_project_memory(project_id: str, key: str) -> dict[str, str]:
        """Delete a shared memory entry for a project."""
        deps.project_repo.get_by_id(project_id)
        deps.memory_repo.delete(project_id, key)
        return {"status": "deleted", "project_id": project_id, "key": key}

    @router.get(
        "/projects/{project_id}/files",
        tags=["projects"],
        responses={404: {"description": "Project not found"}},
    )
    def list_project_files(project_id: str) -> dict[str, list[dict[str, object]]]:
        """List artifact files across all project sessions."""
        deps.project_repo.get_by_id(project_id)
        rows = deps.conversation_repo.list_by_project(project_id)
        files: list[dict[str, object]] = []
        for conv in rows:
            for artifact in deps.artifact_repo.list_by_conversation(conv.id):
                files.append(
                    {
                        "artifact_id": artifact.artifact_id,
                        "conversation_id": artifact.conversation_id,
                        "name": artifact.name,
                        "path": artifact.path,
                        "mime_type": artifact.mime_type,
                        "size_bytes": artifact.size_bytes,
                        "created_at": str(artifact.created_at) if artifact.created_at else "",
                    }
                )
        return {"files": files}

    return router
