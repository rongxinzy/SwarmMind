"""Base agent class — shared DeerFlow-first agent utilities."""

from abc import ABC, abstractmethod

from swarmmind.layered_memory import LayeredMemory
from swarmmind.models import MemoryContext, MemoryLayer, MemoryScope
from swarmmind.repositories.action_proposal import ActionProposalRepository
from swarmmind.repositories.agent import AgentRepository


class AgentError(Exception):
    """Base exception for SwarmMind agent errors."""

    pass


class BaseAgent(ABC):
    """Base class for SwarmMind agents backed by the DeerFlow runtime."""

    def __init__(self, agent_id: str, domain: str) -> None:
        self.agent_id = agent_id
        self.domain = domain
        self.memory = LayeredMemory(agent_id)
        self._system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """Load agent's system prompt from DB."""
        prompt = AgentRepository().get_system_prompt(self.agent_id)
        if prompt is None:
            raise AgentError(f"Agent {self.agent_id} not found in database.")
        return prompt

    @property
    @abstractmethod
    def domain_tags(self) -> list[str]:
        """Domain tags this agent reads from shared memory."""
        raise NotImplementedError

    def _resolve_write_scope(self, ctx: MemoryContext | None) -> MemoryScope:
        """Determine the most specific writable scope from ctx.

        Priority: session_id (L1) > team_id (L2) > project_id (L3) > user_id (L4).
        Agents cannot write to L4 unless they are in SOUL_WRITER_AGENT_IDS,
        but since ctx always provides user_id as a fallback, we fall through
        to the most specific available scope (never L4 for regular agents).
        """
        if ctx is None:
            # No context — use a default user scope (L4, but agent will be denied
            # unless they are soul_writer; this is intentional guardrail)
            return MemoryScope(layer=MemoryLayer.USER_SOUL, scope_id="default_user")
        if ctx.session_id:
            return MemoryScope(layer=MemoryLayer.TMP, scope_id=ctx.session_id)
        if ctx.team_id:
            return MemoryScope(layer=MemoryLayer.TEAM, scope_id=ctx.team_id)
        if ctx.project_id:
            return MemoryScope(layer=MemoryLayer.PROJECT, scope_id=ctx.project_id)
        return MemoryScope(layer=MemoryLayer.USER_SOUL, scope_id=ctx.user_id)

    def _create_rejected_proposal(self, proposal_id: str, description: str) -> None:
        """Update a proposal to rejected status with error description."""
        ActionProposalRepository().reject(proposal_id, description)
