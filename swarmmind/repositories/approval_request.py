"""Approval request repository."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import ApprovalRequestDB
from swarmmind.time_utils import utc_now


class ApprovalRequestRepository:
    """Repository for approval request operations."""

    def create(  # noqa: PLR0913
        self,
        *,
        project_id: str,
        run_id: str | None = None,
        action_proposal_id: str | None = None,
        title: str,
        description: str | None = None,
        risk_tier: str = "medium",
        requested_capability: str | None = None,
        evidence: str | None = None,
        impact: str | None = None,
        approver_role: str | None = None,
        recovery_behavior: str | None = None,
        status: str = "pending",
        decision_reason: str | None = None,
    ) -> ApprovalRequestDB:
        """Create and persist an approval request."""
        with session_scope() as session:
            approval = ApprovalRequestDB(
                approval_id=str(uuid.uuid4()),
                project_id=project_id,
                run_id=run_id,
                action_proposal_id=action_proposal_id,
                title=title,
                description=description,
                risk_tier=risk_tier,
                requested_capability=requested_capability,
                evidence=evidence,
                impact=impact,
                approver_role=approver_role,
                recovery_behavior=recovery_behavior,
                status=status,
                decision_reason=decision_reason,
            )
            session.add(approval)
            session.commit()
            session.refresh(approval)
            session.expunge(approval)
            return approval

    def get(self, approval_id: str) -> ApprovalRequestDB:
        """Get an approval request by ID or raise 404."""
        with session_scope() as session:
            approval = session.get(ApprovalRequestDB, approval_id)
            if approval is None:
                raise HTTPException(status_code=404, detail="Approval request not found")
            session.expunge(approval)
            return approval

    def list_by_project(self, project_id: str) -> list[ApprovalRequestDB]:
        """List approval requests for a project ordered by created_at descending."""
        with session_scope() as session:
            results = session.exec(
                select(ApprovalRequestDB)
                .where(ApprovalRequestDB.project_id == project_id)
                .order_by(ApprovalRequestDB.created_at.desc()),
            ).all()
            for r in results:
                session.expunge(r)
            return list(results)

    def list_by_status(self, status: str) -> list[ApprovalRequestDB]:
        """List approval requests by status ordered by created_at descending."""
        with session_scope() as session:
            results = session.exec(
                select(ApprovalRequestDB)
                .where(ApprovalRequestDB.status == status)
                .order_by(ApprovalRequestDB.created_at.desc()),
            ).all()
            for r in results:
                session.expunge(r)
            return list(results)

    def list_by_filters(
        self,
        project_id: str | None = None,
        status: str | None = None,
        risk_tier: str | None = None,
    ) -> list[ApprovalRequestDB]:
        """List approval requests with optional filters."""
        with session_scope() as session:
            query = select(ApprovalRequestDB)
            if project_id is not None:
                query = query.where(ApprovalRequestDB.project_id == project_id)
            if status is not None:
                query = query.where(ApprovalRequestDB.status == status)
            if risk_tier is not None:
                query = query.where(ApprovalRequestDB.risk_tier == risk_tier)
            query = query.order_by(ApprovalRequestDB.created_at.desc())
            results = session.exec(query).all()
            for r in results:
                session.expunge(r)
            return list(results)

    def update(
        self,
        approval_id: str,
        *,
        status: str | None = None,
        decision_reason: str | None = None,
        title: str | None = None,
        description: str | None = None,
        risk_tier: str | None = None,
    ) -> ApprovalRequestDB:
        """Update approval request fields. Only provided fields are changed."""
        with session_scope() as session:
            approval = session.get(ApprovalRequestDB, approval_id)
            if approval is None:
                raise HTTPException(status_code=404, detail="Approval request not found")

            if status is not None:
                approval.status = status
            if decision_reason is not None:
                approval.decision_reason = decision_reason
            if title is not None:
                approval.title = title
            if description is not None:
                approval.description = description
            if risk_tier is not None:
                approval.risk_tier = risk_tier

            approval.updated_at = utc_now()
            session.commit()
            session.refresh(approval)
            session.expunge(approval)
            return approval

    def delete(self, approval_id: str) -> None:
        """Delete an approval request by ID."""
        with session_scope() as session:
            approval = session.get(ApprovalRequestDB, approval_id)
            if approval is not None:
                session.delete(approval)
