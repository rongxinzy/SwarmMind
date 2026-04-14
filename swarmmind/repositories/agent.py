"""Agent repository."""

from __future__ import annotations

from swarmmind.db import session_scope
from swarmmind.db_models import AgentDB


class AgentRepository:
    """Repository for agent registry operations."""

    def get_system_prompt(self, agent_id: str) -> str | None:
        """Load agent's system prompt from DB."""
        with session_scope() as session:
            agent = session.get(AgentDB, agent_id)
            return agent.system_prompt if agent else None
