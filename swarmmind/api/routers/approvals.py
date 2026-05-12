"""Approval request domain routes."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

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

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ApprovalsRouterDeps:
    """Dependencies for the approvals router."""

    approval_request_repo: object
    project_repo: object
    run_repo: object
    audit_writer: Any | None = field(default=None)


def build_approvals_router(deps: ApprovalsRouterDeps) -> APIRouter:
    """Return an APIRouter with all approval-request CRUD endpoints."""
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

    @router.get(
        "/approvals/{approval_id}", tags=["approvals"], responses={404: {"description": "Approval request not found"}}
    )
    def get_approval(approval_id: str) -> ApprovalRequest:
        """Get a single approval request by ID."""
        return db_to_approval_request(deps.approval_request_repo.get(approval_id))

    @router.patch(
        "/approvals/{approval_id}",
        tags=["approvals"],
        responses={
            404: {"description": "Approval request not found"},
            409: {"description": "Invalid status transition"},
        },
    )
    def update_approval(approval_id: str, body: UpdateApprovalRequest) -> ApprovalRequest:
        """Update an approval request. Only provided fields are changed.

        When status transitions to approved or rejected, the associated run's
        status is updated and an audit entry is written. True mid-stream resume
        is not implemented in this phase — the run is marked completed/failed
        and the user may re-send the original message to continue.
        """
        ar = deps.approval_request_repo.get(approval_id)
        fields: dict[str, object] = {}
        is_decision = False
        if body.status is not None:
            if body.status in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED):
                if ar.status != ApprovalStatus.PENDING.value:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Only pending requests can be approved or rejected. Current status: {ar.status}",
                    )
                is_decision = True
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

        # Apply run-state transition BEFORE persisting the approval status so
        # that if the run update fails the approval stays PENDING and can be
        # retried. Raising here keeps the approval_repo update un-executed.
        if is_decision and ar.run_id:
            _apply_decision_to_run(
                run_id=ar.run_id,
                project_id=ar.project_id,
                approval_id=approval_id,
                decision=body.status.value,  # type: ignore[union-attr]
                reason=body.decision_reason,
                deps=deps,
            )

        updated = deps.approval_request_repo.update(approval_id, **fields)

        return db_to_approval_request(updated)

    @router.delete(
        "/approvals/{approval_id}", tags=["approvals"], responses={404: {"description": "Approval request not found"}}
    )
    def delete_approval(approval_id: str) -> DeleteApprovalResponse:
        """Delete an approval request."""
        deps.approval_request_repo.get(approval_id)
        deps.approval_request_repo.delete(approval_id)
        return DeleteApprovalResponse(approval_id=approval_id)

    return router


def _apply_decision_to_run(
    *,
    run_id: str,
    project_id: str,
    approval_id: str,
    decision: str,
    reason: str | None,
    deps: ApprovalsRouterDeps,
) -> None:
    """Update run status and signal suspension based on an approval decision.

    Raises on run-repo failures so the caller can return an error response and
    the approval stays PENDING (retryable).
    """
    from swarmmind.services import run_suspension

    if decision == ApprovalStatus.APPROVED.value:
        deps.run_repo.mark_completed(run_id, f"Approved — run completed after approval {approval_id}")
    else:
        deps.run_repo.mark_failed(run_id, "approval_rejected", reason or "Approval rejected by operator")

    # Signal any in-process suspension (no-op if run is not suspended in this process).
    run_suspension.resolve(run_id, decision, reason)

    if deps.audit_writer is not None:
        try:
            deps.audit_writer.write(
                event_type="approval.decided",
                project_id=project_id,
                run_id=run_id,
                approval_id=approval_id,
                actor="user",
                actor_type="user",
                decision=decision,
                reason=reason,
            )
        except Exception:
            logger.exception("Failed to write audit for approval decision: approval_id=%s", approval_id)
