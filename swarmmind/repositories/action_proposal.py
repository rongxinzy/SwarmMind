"""Action proposal repository."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import ActionProposalDB
from swarmmind.models import ActionProposal, ProposalStatus


def _db_to_action_proposal(db_proposal: ActionProposalDB) -> ActionProposal:
    return ActionProposal(
        id=db_proposal.id,
        agent_id=db_proposal.agent_id,
        description=db_proposal.description,
        target_resource=db_proposal.target_resource,
        preconditions=json.loads(db_proposal.preconditions) if db_proposal.preconditions else None,
        postconditions=json.loads(db_proposal.postconditions) if db_proposal.postconditions else None,
        confidence=db_proposal.confidence,
        status=ProposalStatus(db_proposal.status),
        created_at=db_proposal.created_at or datetime.utcnow(),
    )


class ActionProposalRepository:
    """Repository for action proposal operations."""

    def get(self, proposal_id: str) -> ActionProposal | None:
        """Fetch a single action proposal by ID."""
        with session_scope() as session:
            db_proposal = session.get(ActionProposalDB, proposal_id)
            return _db_to_action_proposal(db_proposal) if db_proposal else None

    def create(
        self,
        agent_id: str,
        description: str,
        target_resource: str | None = None,
        preconditions: dict | None = None,
        postconditions: dict | None = None,
        confidence: float = 0.5,
    ) -> ActionProposal:
        """Create and persist an action proposal."""
        proposal_id = str(uuid.uuid4())
        with session_scope() as session:
            db_proposal = ActionProposalDB(
                id=proposal_id,
                agent_id=agent_id,
                description=description,
                target_resource=target_resource,
                preconditions=json.dumps(preconditions) if preconditions else None,
                postconditions=json.dumps(postconditions) if postconditions else None,
                confidence=confidence,
                status=ProposalStatus.PENDING.value,
                created_at=datetime.utcnow(),
            )
            session.add(db_proposal)
            session.commit()
            session.refresh(db_proposal)
            return _db_to_action_proposal(db_proposal)

    def update_result(
        self,
        proposal_id: str,
        description: str,
        target_resource: str | None = None,
        confidence: float = 1.0,
    ) -> None:
        """Update an action proposal after agent has processed it."""
        with session_scope() as session:
            proposal = session.get(ActionProposalDB, proposal_id)
            if proposal is not None:
                proposal.description = description
                proposal.target_resource = target_resource
                proposal.confidence = confidence

    def reject(self, proposal_id: str, description: str) -> None:
        """Update a proposal to rejected status with error description."""
        with session_scope() as session:
            proposal = session.get(ActionProposalDB, proposal_id)
            if proposal is not None:
                proposal.status = ProposalStatus.REJECTED.value
                proposal.description = description

    def list_pending(self, limit: int, offset: int) -> tuple[list[ActionProposalDB], int]:
        """List pending proposals paginated. Returns (items, total)."""
        with session_scope() as session:
            total = session.exec(
                select(func.count(ActionProposalDB.id)).where(
                    ActionProposalDB.status == ProposalStatus.PENDING.value,
                ),
            ).one()
            results = session.exec(
                select(ActionProposalDB)
                .where(ActionProposalDB.status == ProposalStatus.PENDING.value)
                .order_by(ActionProposalDB.created_at.asc())
                .limit(limit)
                .offset(offset),
            ).all()
            for r in results:
                session.expunge(r)
            return list(results), total

    def approve(self, proposal_id: str) -> None:
        """Approve a pending proposal. Raises 404/409 HTTPException."""
        with session_scope() as session:
            proposal = session.get(ActionProposalDB, proposal_id)
            if proposal is None:
                raise HTTPException(status_code=404, detail="Proposal not found")
            if proposal.status != ProposalStatus.PENDING.value:
                raise HTTPException(
                    status_code=409,
                    detail=f"Proposal already in status: {proposal.status}",
                )
            proposal.status = ProposalStatus.APPROVED.value

    def reject_proposal(self, proposal_id: str) -> None:
        """Reject a pending proposal. Raises 404/409 HTTPException."""
        with session_scope() as session:
            proposal = session.get(ActionProposalDB, proposal_id)
            if proposal is None:
                raise HTTPException(status_code=404, detail="Proposal not found")
            if proposal.status != ProposalStatus.PENDING.value:
                raise HTTPException(
                    status_code=409,
                    detail=f"Proposal already in status: {proposal.status}",
                )
            proposal.status = ProposalStatus.REJECTED.value

    def list_stale(self, timeout_seconds: int) -> list[ActionProposalDB]:
        """Return proposals pending older than timeout_seconds."""
        with session_scope() as session:
            cutoff = datetime.utcnow() - timedelta(seconds=timeout_seconds)
            results = session.exec(
                select(ActionProposalDB).where(
                    ActionProposalDB.status == ProposalStatus.PENDING.value,
                    ActionProposalDB.created_at < cutoff,
                ),
            ).all()
            for r in results:
                session.expunge(r)
            return list(results)
