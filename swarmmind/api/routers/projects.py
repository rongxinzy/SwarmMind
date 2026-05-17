"""Project domain routes: CRUD, overview, tasks, agent-team, streaming."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from swarmmind.api.routers.mappers import (
    db_to_approval_request,
    db_to_artifact,
    db_to_audit_log_entry,
    db_to_project,
    db_to_run,
    db_to_task,
    db_to_team_instance,
)
from swarmmind.models import (
    ArtifactListResponse,
    AttachTeamRequest,
    AuditLogListResponse,
    CreateTaskRequest,
    DeleteProjectResponse,
    DeleteTaskResponse,
    Project,
    ProjectAgentTeamInstance,
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectOverviewResponse,
    ProjectUpdateRequest,
    RunListResponse,
    SendMessageRequest,
    Task,
    TaskListResponse,
    UpdateTaskRequest,
    UpdateTeamInstanceRequest,
)


@dataclass(frozen=True)
class ProjectsRouterDeps:
    """Dependencies for the projects router."""

    project_repo: object
    task_repo: object
    run_repo: object
    artifact_repo: object
    approval_request_repo: object
    audit_log_repo: object
    agent_team_repo: object
    project_team_repo: object
    conversation_repo: object
    stream_conversation_message: object
    stream_project_message: object


def build_projects_router(deps: ProjectsRouterDeps) -> APIRouter:
    """Return an APIRouter with all project domain endpoints."""
    router = APIRouter()

    def _db_to_project(proj) -> Project:
        return db_to_project(proj, deps.project_team_repo, deps.agent_team_repo)

    def _db_to_team_instance(instance) -> ProjectAgentTeamInstance:
        return db_to_team_instance(instance, deps.agent_team_repo)

    def _ensure_project_conversation(project_id: str) -> str:
        from swarmmind.db import session_scope
        from swarmmind.db_models import ProjectDB

        proj = deps.project_repo.get_by_id(project_id)
        if proj.conversation_id:
            deps.conversation_repo.mark_project_bound(proj.conversation_id)
            return proj.conversation_id
        conv = deps.conversation_repo.create(title=proj.title, title_status="pending")
        deps.conversation_repo.mark_project_bound(conv.id)
        with session_scope() as session:
            proj_db = session.get(ProjectDB, project_id)
            if proj_db is not None:
                proj_db.conversation_id = conv.id
                session.commit()
        return conv.id

    def _attach_team(project_id: str, team_template_id: str | None) -> None:
        import logging

        _logger = logging.getLogger(__name__)
        if team_template_id:
            try:
                deps.agent_team_repo.get_by_id(team_template_id)
                deps.project_team_repo.create(
                    project_id=project_id,
                    team_template_id=team_template_id,
                )
            except Exception as e:
                _logger.warning("Failed to attach team %s to project %s: %s", team_template_id, project_id, e)

    # ---- Project CRUD ----

    @router.get("/projects", tags=["projects"])
    def list_projects(
        limit: Annotated[int | None, Query(ge=1, le=500)] = None,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> ProjectListResponse:
        """List all projects ordered by updated_at descending."""
        rows = deps.project_repo.list_all(limit=limit, offset=offset)
        return ProjectListResponse(items=[_db_to_project(r) for r in rows], total=deps.project_repo.count_all())

    @router.get("/projects/{project_id}", tags=["projects"], responses={404: {"description": "Project not found"}})
    def get_project(project_id: str) -> Project:
        """Get a single project by ID."""
        return _db_to_project(deps.project_repo.get_by_id(project_id))

    @router.post("/projects", tags=["projects"])
    def create_project(body: ProjectCreateRequest) -> Project:
        """Create a new project manually."""
        proj = deps.project_repo.create(
            title=body.title,
            goal=body.goal,
            scope=body.scope,
            constraints=body.constraints,
            source_conversation_id=body.source_conversation_id,
            next_step=body.next_step,
            phase=body.phase,
            risk_level=body.risk_level,
        )
        _ensure_project_conversation(proj.project_id)
        _attach_team(proj.project_id, body.team_template_id)
        return _db_to_project(proj)

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
            return _db_to_project(deps.project_repo.get_by_id(project_id))
        deps.project_repo.update(project_id, **fields)
        return _db_to_project(deps.project_repo.get_by_id(project_id))

    # ---- Project overview / audit / artifacts ----

    @router.get(
        "/projects/{project_id}/overview", tags=["projects"], responses={404: {"description": "Project not found"}}
    )
    def get_project_overview(project_id: str) -> ProjectOverviewResponse:
        """Get aggregated project overview with stats and recent items."""
        proj = deps.project_repo.get_by_id(project_id)
        tasks = deps.task_repo.list_by_project(project_id)
        artifacts = deps.artifact_repo.list_by_project(project_id)
        runs = deps.run_repo.list_by_project(project_id)
        approvals = deps.approval_request_repo.list_by_project(project_id)

        blocked_count = sum(1 for t in tasks if t.status == "blocked")
        pending_approval_count = sum(1 for a in approvals if a.status == "pending")
        stats = {
            "blocked_count": blocked_count,
            "pending_approval_count": pending_approval_count,
            "task_count": len(tasks),
            "artifact_count": len(artifacts),
            "run_count": len(runs),
        }
        recent_limit = 5
        return ProjectOverviewResponse(
            project=_db_to_project(proj),
            stats=stats,
            recent_tasks=[db_to_task(t) for t in tasks[:recent_limit]],
            recent_artifacts=[db_to_artifact(a) for a in artifacts[:recent_limit]],
            recent_runs=[db_to_run(r) for r in runs[:recent_limit]],
            recent_approvals=[db_to_approval_request(a) for a in approvals[:recent_limit]],
        )

    @router.get(
        "/projects/{project_id}/audit", tags=["projects"], responses={404: {"description": "Project not found"}}
    )
    def list_project_audit_logs(project_id: str) -> AuditLogListResponse:
        """List audit log entries for a specific project."""
        deps.project_repo.get_by_id(project_id)
        rows = deps.audit_log_repo.list_by_project(project_id)
        return AuditLogListResponse(
            items=[db_to_audit_log_entry(r) for r in rows],
            total=len(rows),
        )

    @router.get(
        "/projects/{project_id}/artifacts", tags=["projects"], responses={404: {"description": "Project not found"}}
    )
    def list_project_artifacts(project_id: str) -> ArtifactListResponse:
        """List artifacts for a project."""
        deps.project_repo.get_by_id(project_id)
        rows = deps.artifact_repo.list_by_project(project_id)
        return ArtifactListResponse(items=[db_to_artifact(r) for r in rows], total=len(rows))

    @router.get("/projects/{project_id}/runs", tags=["runs"], responses={404: {"description": "Project not found"}})
    def list_project_runs(project_id: str) -> RunListResponse:
        """List runs for a project."""
        deps.project_repo.get_by_id(project_id)
        rows = deps.run_repo.list_by_project(project_id)
        return RunListResponse(items=[db_to_run(r) for r in rows], total=len(rows))

    @router.get(
        "/projects/{project_id}/runs/{run_id}/events",
        tags=["runs"],
        responses={
            404: {"description": "Project or run not found"},
        },
    )
    def list_run_events(project_id: str, run_id: str) -> AuditLogListResponse:
        """List audit/lifecycle events for a specific run within a project."""
        deps.project_repo.get_by_id(project_id)
        deps.run_repo.get_by_id(run_id)
        rows = deps.audit_log_repo.list_by_run(run_id)
        return AuditLogListResponse(
            items=[db_to_audit_log_entry(r) for r in rows],
            total=len(rows),
        )

    # ---- Task routes ----

    @router.get(
        "/projects/{project_id}/tasks", tags=["projects"], responses={404: {"description": "Project not found"}}
    )
    def list_project_tasks(project_id: str) -> TaskListResponse:
        """List tasks for a project."""
        deps.project_repo.get_by_id(project_id)
        rows = deps.task_repo.list_by_project(project_id)
        return TaskListResponse(items=[db_to_task(r) for r in rows], total=len(rows))

    @router.post(
        "/projects/{project_id}/tasks", tags=["projects"], responses={404: {"description": "Project not found"}}
    )
    def create_task(project_id: str, body: CreateTaskRequest) -> Task:
        """Create a new task for a project."""
        deps.project_repo.get_by_id(project_id)
        task = deps.task_repo.create(
            project_id=project_id,
            title=body.title,
            description=body.description,
            status=body.status.value,
            assignee_role=body.assignee_role,
            source_workstream=body.source_workstream,
            artifact_ids=body.artifact_ids,
            priority=body.priority.value,
        )
        return db_to_task(task)

    @router.get(
        "/projects/{project_id}/tasks/{task_id}",
        tags=["projects"],
        responses={404: {"description": "Project or task not found"}},
    )
    def get_task(project_id: str, task_id: str) -> Task:
        """Get a single task by ID."""
        deps.project_repo.get_by_id(project_id)
        task = deps.task_repo.get_by_id(task_id)
        if task.project_id != project_id:
            raise HTTPException(status_code=404, detail="Task not found in this project")
        return db_to_task(task)

    @router.patch(
        "/projects/{project_id}/tasks/{task_id}",
        tags=["projects"],
        responses={404: {"description": "Project or task not found"}},
    )
    def update_task(project_id: str, task_id: str, body: UpdateTaskRequest) -> Task:
        """Update a task. Only provided fields are changed."""
        deps.project_repo.get_by_id(project_id)
        task = deps.task_repo.get_by_id(task_id)
        if task.project_id != project_id:
            raise HTTPException(status_code=404, detail="Task not found in this project")
        fields: dict[str, object] = {}
        if body.title is not None:
            fields["title"] = body.title
        if body.description is not None:
            fields["description"] = body.description
        if body.status is not None:
            fields["status"] = body.status.value
        if body.assignee_role is not None:
            fields["assignee_role"] = body.assignee_role
        if body.source_workstream is not None:
            fields["source_workstream"] = body.source_workstream
        if body.artifact_ids is not None:
            fields["artifact_ids"] = body.artifact_ids
        if body.priority is not None:
            fields["priority"] = body.priority.value
        if not fields:
            return db_to_task(task)
        return db_to_task(deps.task_repo.update(task_id, **fields))

    @router.delete(
        "/projects/{project_id}/tasks/{task_id}",
        tags=["projects"],
        responses={404: {"description": "Project or task not found"}},
    )
    def delete_task(project_id: str, task_id: str) -> DeleteTaskResponse:
        """Delete a task."""
        deps.project_repo.get_by_id(project_id)
        task = deps.task_repo.get_by_id(task_id)
        if task.project_id != project_id:
            raise HTTPException(status_code=404, detail="Task not found in this project")
        deps.task_repo.delete(task_id)
        return DeleteTaskResponse(task_id=task_id)

    # ---- Agent team instance routes ----

    @router.post(
        "/projects/{project_id}/agent-team",
        tags=["projects"],
        status_code=201,
        responses={
            404: {"description": "Project or team template not found"},
            409: {"description": "Project already has a team attached"},
        },
    )
    def attach_team_to_project(project_id: str, body: AttachTeamRequest) -> ProjectAgentTeamInstance:
        """Attach an agent team template to a project."""
        deps.project_repo.get_by_id(project_id)
        instance = deps.project_team_repo.create(
            project_id=project_id,
            team_template_id=body.team_template_id,
            instance_config=body.instance_config,
        )
        return _db_to_team_instance(instance)

    @router.get(
        "/projects/{project_id}/agent-team", tags=["projects"], responses={404: {"description": "Project not found"}}
    )
    def get_project_team(project_id: str) -> ProjectAgentTeamInstance:
        """Get the agent team instance attached to a project."""
        deps.project_repo.get_by_id(project_id)
        instance = deps.project_team_repo.get_by_project(project_id)
        if instance is None:
            raise HTTPException(status_code=404, detail="Project does not have an agent team attached")
        return _db_to_team_instance(instance)

    @router.patch(
        "/projects/{project_id}/agent-team",
        tags=["projects"],
        responses={404: {"description": "Project or team instance not found"}},
    )
    def update_project_team(project_id: str, body: UpdateTeamInstanceRequest) -> ProjectAgentTeamInstance:
        """Update the agent team instance for a project."""
        instance = deps.project_team_repo.update(
            project_id=project_id,
            instance_config=body.instance_config,
            status=body.status,
        )
        return _db_to_team_instance(instance)

    @router.delete("/projects/{project_id}/agent-team", tags=["projects"], status_code=204)
    def detach_team_from_project(project_id: str) -> None:
        """Detach the agent team from a project."""
        deps.project_repo.get_by_id(project_id)
        deps.project_team_repo.delete(project_id)

    # ---- Project streaming ----

    @router.post(
        "/projects/{project_id}/messages/stream",
        tags=["projects"],
        responses={404: {"description": "Project not found"}},
    )
    def send_project_message_stream(project_id: str, body: SendMessageRequest) -> StreamingResponse:
        """Stream a project execution turn, creating a RunDB row anchored on project_id."""
        deps.project_repo.get_by_id(project_id)
        conversation_id = _ensure_project_conversation(project_id)
        return StreamingResponse(
            deps.stream_project_message(project_id, conversation_id, body),
            media_type="application/x-ndjson",
        )

    return router
