"""Base agent class — shared logic for all agents."""

import json
import logging
import re
import uuid
from abc import ABC, abstractmethod
from typing import Any, Optional

from swarmmind.context_broker import create_action_proposal, update_proposal_result
from swarmmind.db import get_connection
from swarmmind.llm import LLMClient, LLMError
from swarmmind.layered_memory import LayeredMemory
from swarmmind.models import ActionProposal, MemoryContext, MemoryLayer, MemoryScope, ProposalStatus

logger = logging.getLogger(__name__)


class AgentError(Exception):
    """Base exception for agent errors."""
    pass


class EmptyLLMResponseError(AgentError):
    """LLM returned an empty or null response."""
    pass


class JSONParseError(AgentError):
    """LLM response was malformed JSON."""
    pass


class BaseAgent(ABC):
    """
    Base class for all SwarmMind agents.

    Each agent:
    1. Has a specialized domain
    2. Reads from layered memory (filtered by domain tags + visible_scopes)
    3. Calls LLM to decide what to do
    4. Proposes an action (ActionProposal)
    """

    def __init__(self, agent_id: str, domain: str):
        self.agent_id = agent_id
        self.domain = domain
        self.memory = LayeredMemory(agent_id)
        self._system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """Load agent's system prompt from DB."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT system_prompt FROM agents WHERE agent_id = ?",
                (self.agent_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise AgentError(f"Agent {self.agent_id} not found in database.")
            return row["system_prompt"]
        finally:
            conn.close()

    @property
    @abstractmethod
    def domain_tags(self) -> list[str]:
        """Domain tags this agent reads from shared memory."""
        raise NotImplementedError

    def _resolve_write_scope(self, ctx: MemoryContext | None) -> MemoryScope:
        """
        Determine the most specific writable scope from ctx.

        Priority: session_id (L1) > team_id (L2) > project_id (L3) > user_id (L4).
        Agents cannot write to L4 unless they are in SOUL_WRITER_AGENT_IDS,
        but since ctx always provides user_id as a fallback, we fall through
        to the most specific available scope (never L4 for regular agents).
        """
        from swarmmind.models import MemoryLayer
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

    def _build_prompt(self, goal: str, ctx: MemoryContext | None = None) -> str:
        """Build the full prompt with goal + relevant layered memory."""
        memory_entries = self.memory.read_all(tags=self.domain_tags, ctx=ctx)

        context_block = ""
        if memory_entries:
            context_lines = []
            for entry in memory_entries:
                tag_str = ",".join(entry.tags) if entry.tags else ""
                context_lines.append(
                    f"[{entry.key}] ({tag_str}): {entry.value}"
                )
            context_block = "\n\n--- Relevant Memory ---\n" + "\n".join(context_lines)
        else:
            context_block = "\n\n(No relevant memory found yet.)"

        return (
            f"<system>\n{self._system_prompt}\n</system>\n\n"
            f"<goal>\n{goal}\n</goal>\n\n"
            f"<instructions>\nYou must respond with ONLY a valid JSON object, no other text. "
            f"Use this exact format:\n"
            f'{{"description": "What you propose to do", "target_resource": "optional resource path", "confidence": 0.0-1.0}}\n'
            f"</instructions>\n{context_block}"
        )

    def _call_llm(self, prompt: str) -> str:
        """Call the configured LLM API via the shared LLMClient."""
        try:
            client = LLMClient()
            return client.complete(prompt, max_tokens=4096)
        except LLMError as e:
            raise AgentError(str(e)) from e

    def act(self, goal: str, action_proposal_id: str, ctx: MemoryContext | None = None) -> ActionProposal:
        """
        Main agent entry point.

        1. Build prompt with goal + shared memory
        2. Call LLM
        3. Parse response (handle JSONDecodeError, empty response)
        4. Update action_proposal in DB
        5. Write relevant context to shared memory
        """
        logger.info(
            "Agent %s acting on goal=%r proposal_id=%s",
            self.agent_id, goal[:100], action_proposal_id,
        )

        prompt = self._build_prompt(goal, ctx)

        try:
            raw_response = self._call_llm(prompt)
        except AgentError as e:
            logger.error("LLM error for agent=%s goal=%r: %s", self.agent_id, goal[:50], e)
            raise

        # Empty response check
        if not raw_response or not raw_response.strip():
            logger.error(
                "Empty LLM response for agent=%s goal=%r. "
                "Creating rejected proposal.",
                self.agent_id, goal[:50],
            )
            self._create_rejected_proposal(
                action_proposal_id,
                f"Agent {self.agent_id} returned empty response. "
                "The LLM did not produce a valid answer for this goal.",
            )
            raise EmptyLLMResponseError(f"Empty response from LLM for agent {self.agent_id}")

        # Parse JSON from response
        try:
            # Strip markdown code fences if present
            cleaned = re.sub(r"^```json\s*", "", raw_response.strip())
            cleaned = re.sub(r"^```\s*$", "", cleaned.strip())
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(
                "JSON parse error for agent=%s: %s. Raw response: %r. "
                "Creating rejected proposal.",
                self.agent_id, e, raw_response[:200],
            )
            self._create_rejected_proposal(
                action_proposal_id,
                f"Agent {self.agent_id} returned malformed JSON: {e}. "
                f"Response: {raw_response[:200]}",
            )
            raise JSONParseError(f"JSON parse error: {e}")

        # Validate required fields
        description = parsed.get("description", "")
        if not description:
            logger.error("LLM response missing 'description' field.")
            self._create_rejected_proposal(
                action_proposal_id,
                f"Agent {self.agent_id} response missing 'description' field.",
            )
            raise JSONParseError("Missing 'description' in LLM response")

        # Update proposal with result
        update_proposal_result(
            proposal_id=action_proposal_id,
            description=description,
            target_resource=parsed.get("target_resource"),
            confidence=parsed.get("confidence", 0.5),
        )

        # Write goal + result to layered memory for future agents
        scope = self._resolve_write_scope(ctx)
        self.memory.write(
            scope=scope,
            key=f"goal:{action_proposal_id}",
            value=json.dumps({"goal": goal, "description": description, "agent": self.agent_id}),
            tags=[self.domain],
        )

        logger.info(
            "Agent %s completed: proposal_id=%s description=%s",
            self.agent_id, action_proposal_id, description[:80],
        )

        # Return updated proposal
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM action_proposals WHERE id = ?", (action_proposal_id,))
            row = cursor.fetchone()
            return ActionProposal(**dict(row))
        finally:
            conn.close()

    def _create_rejected_proposal(self, proposal_id: str, description: str) -> None:
        """Update a proposal to rejected status with error description."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE action_proposals SET status = ?, description = ? WHERE id = ?",
                (ProposalStatus.REJECTED.value, description, proposal_id),
            )
            conn.commit()
        finally:
            conn.close()
