"""Context Broker — routes goals to agents, manages strategy table."""

import logging
import re
import uuid
from datetime import datetime
from typing import Optional

from swarmmind.db import get_connection
from swarmmind.models import (
    ActionProposal,
    DispatchResponse,
    EventLogEntry,
    MemoryContext,
    ProposalStatus,
    SupervisorDecision,
)

logger = logging.getLogger(__name__)

# Phase 1 keyword routing rules
ROUTING_KEYWORDS = {
    "finance": [
        "finance", "financial", "revenue", "expense", "profit", "loss",
        "quarterly", "Q1", "Q2", "Q3", "Q4", "annual", "fiscal",
        "budget", "forecast", "income statement", "balance sheet",
    ],
    "code_review": [
        "code", "review", "PR", "pull request", "git", "python",
        "bug", "error", "refactor", "test", "implementation",
        "function", "class", "module", "api", "backend", "frontend",
    ],
}


def derive_situation_tag(goal: str) -> str:
    """
    Derive a situation tag from goal text using keyword extraction.
    Phase 1 placeholder — Phase 2 should use embeddings.
    """
    goal_lower = goal.lower()
    tags = []

    # Check each domain's keywords
    for domain, keywords in ROUTING_KEYWORDS.items():
        for kw in keywords:
            if kw in goal_lower:
                tags.append(domain)
                break

    if tags:
        # Return the most specific match (could be multiple, pick first)
        return tags[0]

    # Fallback: generic tag
    return "unknown"


def route_to_agent(situation_tag: str) -> Optional[str]:
    """
    Look up strategy_table for the given situation_tag.
    Returns agent_id or None if not found.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT agent_id FROM strategy_table WHERE situation_tag = ?",
            (situation_tag,),
        )
        row = cursor.fetchone()
        return row["agent_id"] if row else None
    finally:
        conn.close()


def create_action_proposal(
    agent_id: str,
    description: str,
    target_resource: Optional[str] = None,
    preconditions: Optional[dict] = None,
    postconditions: Optional[dict] = None,
    confidence: float = 0.5,
) -> ActionProposal:
    """Create and persist an action proposal."""
    proposal_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO action_proposals
            (id, agent_id, description, target_resource, preconditions, postconditions, confidence, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                proposal_id,
                agent_id,
                description,
                target_resource,
                str(preconditions) if preconditions else None,
                str(postconditions) if postconditions else None,
                confidence,
                ProposalStatus.PENDING.value,
            ),
        )
        conn.commit()

        cursor.execute("SELECT created_at FROM action_proposals WHERE id = ?", (proposal_id,))
        created_at = cursor.fetchone()["created_at"]

        logger.info(
            "Action proposal created: id=%s agent_id=%s description=%s",
            proposal_id, agent_id, description[:50],
        )

        return ActionProposal(
            id=proposal_id,
            agent_id=agent_id,
            description=description,
            target_resource=target_resource,
            preconditions=preconditions,
            postconditions=postconditions,
            confidence=confidence,
            status=ProposalStatus.PENDING,
            created_at=created_at,
        )
    finally:
        conn.close()


def log_dispatch(
    goal: str,
    situation_tag: str,
    dispatched_agent_id: str,
    action_proposal_id: str,
) -> None:
    """Log a dispatch event to event_log."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO event_log
            (goal, situation_tag, dispatched_agent_id, action_proposal_id, outcome)
            VALUES (?, ?, ?, ?, 'pending')
            """,
            (goal, situation_tag, dispatched_agent_id, action_proposal_id),
        )
        conn.commit()
    finally:
        conn.close()


def dispatch(
    goal: str,
    user_id: str = "default_user",
    project_id: str | None = None,
    team_id: str | None = None,
    session_id: str | None = None,
) -> DispatchResponse:
    """
    Main dispatch entry point.

    1. Build MemoryContext from scope parameters
    2. Derive situation_tag from goal (keyword extraction)
    3. Look up strategy_table for routing
    4. Log to event_log
    5. Return action_proposal_id for supervisor review + MemoryContext
    """
    memory_ctx = MemoryContext(
        user_id=user_id,
        project_id=project_id,
        team_id=team_id,
        session_id=session_id,
    )
    situation_tag = derive_situation_tag(goal)
    agent_id = route_to_agent(situation_tag)

    if agent_id is None:
        logger.warning(
            "No routing found for situation_tag=%s (goal=%r). "
            "Returning error response.",
            situation_tag, goal[:100],
        )
        # Create a rejected proposal so supervisor sees the failure
        proposal = create_action_proposal(
            agent_id="unknown",
            description=f"No agent found for situation: {situation_tag}. "
                       f"Goal text: {goal[:200]}",
            confidence=0.0,
        )
        # Update status to rejected since routing failed
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE action_proposals SET status = ? WHERE id = ?",
                (ProposalStatus.REJECTED.value, proposal.id),
            )
            conn.commit()
        finally:
            conn.close()

        return DispatchResponse(
            action_proposal_id=proposal.id,
            agent_id="unknown",
            status="no_route",
            memory_ctx=memory_ctx,
        )

    # Create a placeholder proposal — the actual agent will update description
    proposal = create_action_proposal(
        agent_id=agent_id,
        description=f"[Agent {agent_id} is processing goal: {goal[:100]}...]",
        confidence=0.5,
    )

    log_dispatch(goal, situation_tag, agent_id, proposal.id)

    logger.info(
        "Dispatched: goal=%r situation_tag=%s agent_id=%s proposal_id=%s",
        goal[:50], situation_tag, agent_id, proposal.id,
    )

    return DispatchResponse(
        action_proposal_id=proposal.id,
        agent_id=agent_id,
        status="pending",
        memory_ctx=memory_ctx,
    )


def update_proposal_result(
    proposal_id: str,
    description: str,
    target_resource: Optional[str] = None,
    confidence: float = 1.0,
) -> None:
    """Update an action proposal after agent has processed it."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE action_proposals
            SET description = ?, target_resource = ?, confidence = ?
            WHERE id = ?
            """,
            (description, target_resource, confidence, proposal_id),
        )
        conn.commit()
    finally:
        conn.close()


def record_supervisor_decision(
    action_proposal_id: str,
    decision: SupervisorDecision,
) -> None:
    """Record supervisor approve/reject/timeout in event_log."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE event_log
            SET supervisor_decision = ?, outcome = ?
            WHERE action_proposal_id = ?
            """,
            (decision.value, "success" if decision == SupervisorDecision.APPROVED else "failure", action_proposal_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_strategy_on_outcome(
    situation_tag: str,
    agent_id: str,
    success: bool,
) -> None:
    """Update success/failure counts in strategy_table after a completed task."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if success:
            cursor.execute(
                "UPDATE strategy_table SET success_count = success_count + 1 "
                "WHERE situation_tag = ? AND agent_id = ?",
                (situation_tag, agent_id),
            )
        else:
            cursor.execute(
                "UPDATE strategy_table SET failure_count = failure_count + 1 "
                "WHERE situation_tag = ? AND agent_id = ?",
                (situation_tag, agent_id),
            )
        conn.commit()
    finally:
        conn.close()
