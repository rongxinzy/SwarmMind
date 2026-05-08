"""Audit log domain routes."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter

from swarmmind.api.routers.mappers import db_to_audit_log_entry
from swarmmind.models import (
    AuditLogEntry,
    AuditLogListResponse,
    CreateAuditLogEntry,
    DeleteAuditLogResponse,
)


@dataclass(frozen=True)
class AuditLogsRouterDeps:
    """Dependencies for the audit-logs router."""

    audit_log_repo: object
    project_repo: object
    run_repo: object
    approval_request_repo: object


def build_audit_logs_router(deps: AuditLogsRouterDeps) -> APIRouter:
    """Return an APIRouter with all audit-log CRUD endpoints."""
    router = APIRouter()

    @router.get("/audit-logs", tags=["audit-logs"])
    def list_audit_logs(
        project_id: str | None = None,
        run_id: str | None = None,
        approval_id: str | None = None,
    ) -> AuditLogListResponse:
        """List audit log entries with optional filters."""
        rows = deps.audit_log_repo.list_by_filters(
            project_id=project_id,
            run_id=run_id,
            approval_id=approval_id,
        )
        return AuditLogListResponse(
            items=[db_to_audit_log_entry(r) for r in rows],
            total=len(rows),
        )

    @router.post("/audit-logs", tags=["audit-logs"], responses={404: {"description": "Project not found"}})
    def create_audit_log(body: CreateAuditLogEntry) -> AuditLogEntry:
        """Create a new audit log entry."""
        deps.project_repo.get_by_id(body.project_id)
        if body.run_id:
            deps.run_repo.get_by_id(body.run_id)
        if body.approval_id:
            deps.approval_request_repo.get(body.approval_id)
        entry = deps.audit_log_repo.create(
            audit_type=body.audit_type,
            project_id=body.project_id,
            run_id=body.run_id,
            approval_id=body.approval_id,
            actor_id=body.actor_id,
            actor_type=body.actor_type,
            decision=body.decision,
            reason=body.reason,
            extra_data=body.metadata,
        )
        return db_to_audit_log_entry(entry)

    @router.get(
        "/audit-logs/{audit_id}", tags=["audit-logs"], responses={404: {"description": "Audit log entry not found"}}
    )
    def get_audit_log(audit_id: str) -> AuditLogEntry:
        """Get a single audit log entry by ID."""
        return db_to_audit_log_entry(deps.audit_log_repo.get(audit_id))

    @router.delete(
        "/audit-logs/{audit_id}", tags=["audit-logs"], responses={404: {"description": "Audit log entry not found"}}
    )
    def delete_audit_log(audit_id: str) -> DeleteAuditLogResponse:
        """Delete an audit log entry."""
        deps.audit_log_repo.get(audit_id)
        deps.audit_log_repo.delete(audit_id)
        return DeleteAuditLogResponse(audit_id=audit_id)

    return router
