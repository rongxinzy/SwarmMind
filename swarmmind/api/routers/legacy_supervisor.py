"""Legacy supervisor routes: pending proposals, approve, reject, dispatch, strategy."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException

from swarmmind.models import (
    ApproveResponse,
    DispatchResponse,
    GoalRequest,
    PendingResponse,
    RejectRequest,
    RejectResponse,
    StrategyEntry,
    StrategyResponse,
    SupervisorDecision,
)
from swarmmind.repositories.action_proposal import _db_to_action_proposal


@dataclass(frozen=True)
class LegacySupervisorRouterDeps:
    """Dependencies for the legacy supervisor router."""

    action_proposal_repo: object
    strategy_repo: object
    record_supervisor_decision: Callable
    dispatch: Callable


def build_legacy_supervisor_router(deps: LegacySupervisorRouterDeps) -> APIRouter:
    """Return an APIRouter for legacy supervisor routes (pending, approve, reject, dispatch, strategy)."""
    router = APIRouter()

    @router.get("/pending", tags=["supervisor"])
    def get_pending(limit: int = 50, offset: int = 0) -> PendingResponse:
        """List pending action proposals (paginated)."""
        rows, total = deps.action_proposal_repo.list_pending(limit=limit, offset=offset)
        items = [_db_to_action_proposal(row) for row in rows]
        return PendingResponse(items=items, total=total)

    @router.post("/approve/{proposal_id}", tags=["supervisor"], responses={404: {"description": "Proposal not found"}})
    def approve(proposal_id: str) -> ApproveResponse:
        """Approve an action proposal."""
        deps.action_proposal_repo.approve(proposal_id)
        deps.record_supervisor_decision(proposal_id, SupervisorDecision.APPROVED)
        return ApproveResponse(id=proposal_id)

    @router.post("/reject/{proposal_id}", tags=["supervisor"], responses={404: {"description": "Proposal not found"}})
    def reject(proposal_id: str, body: RejectRequest | None = None) -> RejectResponse:
        """Reject an action proposal."""
        deps.action_proposal_repo.reject_proposal(proposal_id)
        deps.record_supervisor_decision(proposal_id, SupervisorDecision.REJECTED)
        reason = body.reason if body else None
        return RejectResponse(id=proposal_id, reason=reason)

    @router.get("/strategy", tags=["supervisor"])
    def get_strategy() -> StrategyResponse:
        """View the strategy routing table."""
        rows = deps.strategy_repo.list_all()
        entries = [
            StrategyEntry(
                situation_tag=row.situation_tag,
                agent_id=row.agent_id,
                success_count=row.success_count,
                failure_count=row.failure_count,
            )
            for row in rows
        ]
        return StrategyResponse(entries=entries)

    @router.post("/dispatch", tags=["supervisor"])
    def post_dispatch(body: GoalRequest) -> DispatchResponse:
        """Submit a new goal for dispatch to an agent."""
        try:
            session_id = str(uuid.uuid4())
            return deps.dispatch(body.goal, user_id="supervisor", session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router
