"""Run domain routes."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter

from swarmmind.api.routers.mappers import db_to_run
from swarmmind.models import (
    CreateRunRequest,
    Run,
    RunListResponse,
    UpdateRunRequest,
)


@dataclass(frozen=True)
class RunsRouterDeps:
    """Dependencies for the runs router."""

    run_repo: object
    project_repo: object
    conversation_repo: object


def build_runs_router(deps: RunsRouterDeps) -> APIRouter:
    """Return an APIRouter with all run CRUD endpoints."""
    router = APIRouter()

    @router.get(
        "/conversations/{conversation_id}/runs",
        tags=["runs"],
        responses={404: {"description": "Conversation not found"}},
    )
    def list_conversation_runs(conversation_id: str) -> RunListResponse:
        """List runs for a conversation."""
        deps.conversation_repo.get_by_id(conversation_id)
        rows = deps.run_repo.list_by_conversation(conversation_id)
        return RunListResponse(items=[db_to_run(r) for r in rows], total=len(rows))

    @router.get("/runs/{run_id}", tags=["runs"], responses={404: {"description": "Run not found"}})
    def get_run(run_id: str) -> Run:
        """Get a single run by ID."""
        return db_to_run(deps.run_repo.get_by_id(run_id))

    @router.post("/runs", tags=["runs"])
    def create_run(body: CreateRunRequest) -> Run:
        """Create a run record linked to a conversation and/or a project."""
        if body.conversation_id:
            deps.conversation_repo.get_by_id(body.conversation_id)
        if body.project_id:
            deps.project_repo.get_by_id(body.project_id)
        run = deps.run_repo.create(
            conversation_id=body.conversation_id,
            project_id=body.project_id,
            goal=body.goal,
            status=body.status.value,
        )
        return db_to_run(run)

    @router.patch("/runs/{run_id}", tags=["runs"], responses={404: {"description": "Run not found"}})
    def update_run(run_id: str, body: UpdateRunRequest) -> Run:
        """Update a run. Only provided fields are changed."""
        run = deps.run_repo.update(
            run_id,
            project_id=body.project_id,
            status=body.status.value if body.status else None,
            goal=body.goal,
            summary=body.summary,
        )
        return db_to_run(run)

    return router
