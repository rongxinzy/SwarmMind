"""Event log repository."""

from __future__ import annotations

from datetime import datetime

from swarmmind.db import session_scope
from swarmmind.db_models import EventLogDB
from swarmmind.models import SupervisorDecision


class EventLogRepository:
    """Repository for event log operations."""

    def create(
        self,
        goal: str,
        situation_tag: str,
        dispatched_agent_id: str,
        action_proposal_id: str,
    ) -> None:
        """Log a dispatch event to event_log."""
        with session_scope() as session:
            entry = EventLogDB(
                goal=goal,
                situation_tag=situation_tag,
                dispatched_agent_id=dispatched_agent_id,
                action_proposal_id=action_proposal_id,
                outcome="pending",
                timestamp=datetime.utcnow(),
            )
            session.add(entry)

    def record_supervisor_decision(
        self,
        action_proposal_id: str,
        decision: SupervisorDecision,
    ) -> None:
        """Record supervisor approve/reject/timeout in event_log."""
        with session_scope() as session:
            from sqlmodel import select
            result = session.exec(
                select(EventLogDB).where(
                    EventLogDB.action_proposal_id == action_proposal_id,
                ),
            ).first()
            if result is not None:
                result.supervisor_decision = decision.value
                result.outcome = (
                    "success" if decision == SupervisorDecision.APPROVED else "failure"
                )
