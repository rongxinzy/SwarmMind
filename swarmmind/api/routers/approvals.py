"""Approval request domain routes."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, HTTPException

from swarmmind.api.routers.mappers import db_to_approval_request
from swarmmind.models import (
    ApprovalRequest,
    ApprovalRequestListResponse,
    ApprovalStatus,
    CreateApprovalRequest,
    DeleteApprovalResponse,
    UpdateApprovalRequest,
)


@dataclass(frozen=True)
class ApprovalsRouterDeps:
    approval_request_repo: object
    project_repo: object
    run_repo: object


def build_approvals_router(deps: ApprovalsRouterDeps) -> APIRouter:
    router = APIRouter()

    @router.get("/approvals", tags=["approvals"])
    def list_approvals(
        project_id: str | None = None,
        status: str | None = None,
        risk_tier: str | None = None,
    ) -> ApprovalRequestListResponse:
        """List approval requests with optional filters."""
        rows = deps.approval_request_repo.list_by_filters(
            project_id=project_id,
            status=status,
            risk_tier=risk_tier,
        )
        return ApprovalRequestListResponse(
            items=[db_to_approval_request(r) for r in rows],
            total=len(rows),
        )

    @router.post("/approvals", tags=["approvals"], responses={404: {"description": "Project not found"}})
    def create_approval(body: CreateApprovalRequest) -> ApprovalRequest:
        """Create a new approval request."""
        deps.project_repo.get_by_id(body.project_id)
        if body.run_id:
            deps.run_repo.get_by_id(body.run_id)
        ar = deps.approval_request_repo.create(
            project_id=body.project_id,
            run_id=body.run_id,
            title=body.title,
            description=body.description,
            risk_tier=body.risk_tier.value,
            requested_capability=body.requested_capability,
            evidence=body.evidence,
            impact=body.impact,
            approver_role=body.approver_role,
            recovery_behavior=body.recovery_behavior,
        )
        return db_to_approval_request(ar)

    @router.get("/approvals/{approval_id}", tags=["approvals"], responses={404: {"description": "Approval request not found"}})
    def get_approval(approval_id: str) -> ApprovalRequest:
        """Get a single approval request by ID."""
        return db_to_approval_request(deps.approval_request_repo.get(approval_id))

    @router.patch(
        "/approvals/{approval_id}",
        tags=["approvals"],
        responses={404: {"description": "Approval request not found"}, 409: {"description": "Invalid status transition"}},
    )
    def update_approval(approval_id: str, body: UpdateApprovalRequest) -> ApprovalRequest:
        """Update an approval request. Only provided fields are changed."""
        ar = deps.approval_request_repo.get(approval_id)
        fields: dict[str, object] = {}
        if body.status is not None:
            if body.status in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED):
                if ar.status != ApprovalStatus.PENDING.value:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Only pending requests can be approved or rejected. Current status: {ar.status}",
                    )
            fields["status"] = body.status.value
        if body.decision_reason is not None:
            fields["decision_reason"] = body.decision_reason
        if body.title is not None:
            fields["title"] = body.title
        if body.description is not None:
            fields["description"] = body.description
        if body.risk_tier is not None:
            fields["risk_tier"] = body.risk_tier.value
        if not fields:
            return db_to_approval_request(ar)
        return db_to_approval_request(deps.approval_request_repo.update(approval_id, **fields))

    @router.delete("/approvals/{approval_id}", tags=["approvals"], responses={404: {"description": "Approval request not found"}})
    def delete_approval(approval_id: str) -> DeleteApprovalResponse:
        """Delete an approval request."""
        deps.approval_request_repo.get(approval_id)
        deps.approval_request_repo.delete(approval_id)
        return DeleteApprovalResponse(approval_id=approval_id)

    return router
