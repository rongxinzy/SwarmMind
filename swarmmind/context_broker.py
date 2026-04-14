"""Context Broker — routes goals to agents, manages strategy table."""

import logging

from swarmmind.models import (
    ActionProposal,
    DispatchResponse,
    MemoryContext,
    SupervisorDecision,
)
from swarmmind.repositories.action_proposal import ActionProposalRepository
from swarmmind.repositories.event_log import EventLogRepository
from swarmmind.repositories.strategy import StrategyRepository

logger = logging.getLogger(__name__)

# Phase 1 keyword routing rules
ROUTING_KEYWORDS = {
    "finance": [
        "finance",
        "financial",
        "revenue",
        "expense",
        "profit",
        "loss",
        "quarterly",
        "Q1",
        "Q2",
        "Q3",
        "Q4",
        "annual",
        "fiscal",
        "budget",
        "forecast",
        "income statement",
        "balance sheet",
    ],
    "code_review": [
        "code",
        "review",
        "PR",
        "pull request",
        "git",
        "python",
        "bug",
        "error",
        "refactor",
        "test",
        "implementation",
        "function",
        "class",
        "module",
        "api",
        "backend",
        "frontend",
    ],
}


def derive_situation_tag(goal: str) -> str:
    """Derive a situation tag from goal text using keyword extraction.
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


def route_to_agent(situation_tag: str) -> str | None:
    """Look up strategy_table for the given situation_tag.

    DeerFlow-first mode always falls back to the ``general`` runtime entrypoint
    when no dedicated control-plane mapping exists yet.
    """
    agent_id = StrategyRepository().get_agent_id(situation_tag)
    return agent_id if agent_id else "general"


def create_action_proposal(
    agent_id: str,
    description: str,
    target_resource: str | None = None,
    preconditions: dict | None = None,
    postconditions: dict | None = None,
    confidence: float = 0.5,
) -> ActionProposal:
    """Create and persist an action proposal."""
    return ActionProposalRepository().create(
        agent_id=agent_id,
        description=description,
        target_resource=target_resource,
        preconditions=preconditions,
        postconditions=postconditions,
        confidence=confidence,
    )


def log_dispatch(
    goal: str,
    situation_tag: str,
    dispatched_agent_id: str,
    action_proposal_id: str,
) -> None:
    """Log a dispatch event to event_log."""
    EventLogRepository().create(
        goal=goal,
        situation_tag=situation_tag,
        dispatched_agent_id=dispatched_agent_id,
        action_proposal_id=action_proposal_id,
    )


def dispatch(
    goal: str,
    user_id: str = "default_user",
    project_id: str | None = None,
    team_id: str | None = None,
    session_id: str | None = None,
    override_situation_tag: str | None = None,
) -> DispatchResponse:
    """Main dispatch entry point.

    1. Build MemoryContext from scope parameters
    2. Derive situation_tag from goal (keyword extraction), or use override_situation_tag if provided
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
    situation_tag = override_situation_tag or derive_situation_tag(goal)
    agent_id = route_to_agent(situation_tag)

    # Create a placeholder proposal — the actual agent will update description
    proposal = create_action_proposal(
        agent_id=agent_id,
        description=f"[Agent {agent_id} is processing goal: {goal[:100]}...]",
        confidence=0.5,
    )

    log_dispatch(goal, situation_tag, agent_id, proposal.id)

    logger.info(
        "Dispatched: goal=%r situation_tag=%s agent_id=%s proposal_id=%s",
        goal[:50],
        situation_tag,
        agent_id,
        proposal.id,
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
    target_resource: str | None = None,
    confidence: float = 1.0,
) -> None:
    """Update an action proposal after agent has processed it."""
    ActionProposalRepository().update_result(
        proposal_id=proposal_id,
        description=description,
        target_resource=target_resource,
        confidence=confidence,
    )


def record_supervisor_decision(
    action_proposal_id: str,
    decision: SupervisorDecision,
) -> None:
    """Record supervisor approve/reject/timeout in event_log."""
    EventLogRepository().record_supervisor_decision(action_proposal_id, decision)


def update_strategy_on_outcome(
    situation_tag: str,
    agent_id: str,
    success: bool,
) -> None:
    """Update success/failure counts in strategy_table after a completed task."""
    del agent_id
    StrategyRepository().update_outcome(situation_tag, success)
