"""Project membership and minimal RBAC routes."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, HTTPException

from swarmmind.api.routers.mappers import db_to_project_membership, project_role_capabilities
from swarmmind.models import (
    ProjectCapability,
    ProjectMemberRole,
    ProjectMembership,
    ProjectMembershipCreateRequest,
    ProjectMembershipDeleteResponse,
    ProjectMembershipListResponse,
    ProjectMembershipUpdateRequest,
    ProjectPermissionCheckResponse,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProjectMembershipRouterDeps:
    """Dependencies for the project membership router."""

    project_repo: object
    membership_repo: object
    audit_writer: Any | None = field(default=None)


def build_project_membership_router(deps: ProjectMembershipRouterDeps) -> APIRouter:
    """Return project membership and permission-check endpoints."""
    router = APIRouter()

    def _ensure_project(project_id: str) -> None:
        deps.project_repo.get_by_id(project_id)

    def _write_audit(
        *,
        project_id: str,
        event_type: str,
        member_id: str,
        role: str | None = None,
        status: str | None = None,
        reason: str | None = None,
    ) -> None:
        if deps.audit_writer is None:
            return
        try:
            deps.audit_writer.write(
                event_type=event_type,
                project_id=project_id,
                actor="system",
                actor_type="system",
                decision=status,
                reason=reason,
                evidence={"member_id": member_id, "role": role, "status": status},
            )
        except Exception:
            logger.exception(
                "Failed to write project membership audit event: project_id=%s member_id=%s", project_id, member_id
            )

    @router.get(
        "/projects/{project_id}/members",
        tags=["project-members"],
        responses={404: {"description": "Project not found"}},
    )
    def list_project_members(project_id: str) -> ProjectMembershipListResponse:
        """List project members."""
        _ensure_project(project_id)
        rows = deps.membership_repo.list_by_project(project_id)
        return ProjectMembershipListResponse(items=[db_to_project_membership(row) for row in rows], total=len(rows))

    @router.post(
        "/projects/{project_id}/members",
        tags=["project-members"],
        status_code=201,
        responses={404: {"description": "Project not found"}, 409: {"description": "Member already exists"}},
    )
    def add_project_member(project_id: str, body: ProjectMembershipCreateRequest) -> ProjectMembership:
        """Add a member to a project."""
        _ensure_project(project_id)
        row = deps.membership_repo.create(
            project_id=project_id,
            member_id=body.member_id,
            display_name=body.display_name,
            role=body.role.value,
            status=body.status.value,
        )
        _write_audit(
            project_id=project_id,
            event_type="member.added",
            member_id=body.member_id,
            role=body.role.value,
            status=body.status.value,
            reason="Project member added",
        )
        return db_to_project_membership(row)

    @router.get(
        "/projects/{project_id}/members/{member_id}",
        tags=["project-members"],
        responses={404: {"description": "Project or member not found"}},
    )
    def get_project_member(project_id: str, member_id: str) -> ProjectMembership:
        """Get one project member by project and member ID."""
        _ensure_project(project_id)
        return db_to_project_membership(deps.membership_repo.get_by_member(project_id, member_id))

    @router.patch(
        "/projects/{project_id}/members/{member_id}",
        tags=["project-members"],
        responses={404: {"description": "Project or member not found"}},
    )
    def update_project_member(
        project_id: str,
        member_id: str,
        body: ProjectMembershipUpdateRequest,
    ) -> ProjectMembership:
        """Update project member role, status, or display name."""
        _ensure_project(project_id)
        current = deps.membership_repo.get_by_member(project_id, member_id)
        fields: dict[str, object] = {}
        if body.display_name is not None:
            fields["display_name"] = body.display_name
        if body.role is not None:
            fields["role"] = body.role.value
        if body.status is not None:
            fields["status"] = body.status.value
        if not fields:
            return db_to_project_membership(current)
        row = deps.membership_repo.update(current.membership_id, **fields)
        _write_audit(
            project_id=project_id,
            event_type="member.updated",
            member_id=member_id,
            role=row.role,
            status=row.status,
            reason="Project member updated",
        )
        return db_to_project_membership(row)

    @router.delete(
        "/projects/{project_id}/members/{member_id}",
        tags=["project-members"],
        responses={404: {"description": "Project or member not found"}},
    )
    def remove_project_member(project_id: str, member_id: str) -> ProjectMembershipDeleteResponse:
        """Remove a project member."""
        _ensure_project(project_id)
        current = deps.membership_repo.get_by_member(project_id, member_id)
        deps.membership_repo.delete(current.membership_id)
        _write_audit(
            project_id=project_id,
            event_type="member.removed",
            member_id=member_id,
            role=current.role,
            status="deleted",
            reason="Project member removed",
        )
        return ProjectMembershipDeleteResponse(membership_id=current.membership_id, member_id=member_id)

    @router.get(
        "/projects/{project_id}/members/{member_id}/permissions/{capability}",
        tags=["project-members"],
        responses={404: {"description": "Project not found"}},
    )
    def check_project_permission(
        project_id: str,
        member_id: str,
        capability: ProjectCapability,
    ) -> ProjectPermissionCheckResponse:
        """Check whether a project member has a capability."""
        _ensure_project(project_id)
        try:
            member = deps.membership_repo.get_by_member(project_id, member_id)
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
            return ProjectPermissionCheckResponse(
                project_id=project_id,
                member_id=member_id,
                capability=capability,
                allowed=False,
                role=None,
                reason="member_not_found",
            )
        if member.status != "active":
            return ProjectPermissionCheckResponse(
                project_id=project_id,
                member_id=member_id,
                capability=capability,
                allowed=False,
                role=ProjectMemberRole(member.role),
                reason="member_inactive",
            )
        capabilities = project_role_capabilities(member.role)
        allowed = capability in capabilities
        return ProjectPermissionCheckResponse(
            project_id=project_id,
            member_id=member_id,
            capability=capability,
            allowed=allowed,
            role=ProjectMemberRole(member.role),
            reason="allowed" if allowed else "role_lacks_capability",
        )

    return router
