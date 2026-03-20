"""Base agent class — shared logic for all agents."""

import json
import logging
import os
import re
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Optional

import httpx

from swarmmind.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_PROVIDER
from swarmmind.context_broker import create_action_proposal, update_proposal_result
from swarmmind.db import get_connection
from swarmmind.models import ActionProposal, ProposalStatus
from swarmmind.shared_memory import SharedMemory

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
    2. Reads from shared memory (filtered by domain tags)
    3. Calls LLM to decide what to do
    4. Proposes an action (ActionProposal)
    """

    def __init__(self, agent_id: str, domain: str):
        self.agent_id = agent_id
        self.domain = domain
        self.memory = SharedMemory(agent_id)
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

    def _build_prompt(self, goal: str) -> str:
        """Build the full prompt with goal + relevant shared memory."""
        memory_entries = []
        for tag in self.domain_tags:
            entries = self.memory.read_all_by_tag(tag)
            memory_entries.extend(entries)

        context_block = ""
        if memory_entries:
            context_lines = []
            for entry in memory_entries:
                context_lines.append(
                    f"[{entry['key']}] ({entry.get('domain_tags', '')}): {entry['value']}"
                )
            context_block = "\n\n--- Relevant Shared Memory ---\n" + "\n".join(context_lines)
        else:
            context_block = "\n\n(No relevant shared memory found yet.)"

        return (
            f"<system>\n{self._system_prompt}\n</system>\n\n"
            f"<goal>\n{goal}\n</goal>\n\n"
            f"<instructions>\nYou must respond with ONLY a valid JSON object, no other text. "
            f"Use this exact format:\n"
            f'{{"description": "What you propose to do", "target_resource": "optional resource path", "confidence": 0.0-1.0}}\n'
            f"</instructions>\n{context_block}"
        )

    def _call_llm(self, prompt: str) -> str:
        """Call the configured LLM API."""
        if LLM_PROVIDER == "anthropic":
            return self._call_anthropic(prompt)
        return self._call_openai(prompt)

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI-compatible API."""
        api_key = LLM_API_KEY or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise AgentError("OPENAI_API_KEY not set")

        base_url = LLM_BASE_URL or "https://api.openai.com/v1"
        url = f"{base_url.rstrip('/')}/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4096,
            "temperature": 0.3,
        }

        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]

        logger.debug("LLM raw response (first 200 chars): %s", content[:200])
        return content

    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API."""
        api_key = LLM_API_KEY or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise AgentError("ANTHROPIC_API_KEY not set")

        base_url = LLM_BASE_URL or "https://api.anthropic.com/v1"
        url = f"{base_url.rstrip('/')}/messages"

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4096,
        }

        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            content = data["content"][0]["text"]

        logger.debug("LLM raw response (first 200 chars): %s", content[:200])
        return content

    def act(self, goal: str, action_proposal_id: str) -> ActionProposal:
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

        prompt = self._build_prompt(goal)

        try:
            raw_response = self._call_llm(prompt)
        except httpx.TimeoutException:
            logger.error("LLM timeout for agent=%s goal=%r", self.agent_id, goal[:50])
            raise AgentError(f"LLM timeout for agent {self.agent_id}")

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

        # Write goal + result to shared memory for future agents
        self.memory.write(
            key=f"goal:{action_proposal_id}",
            value=json.dumps({"goal": goal, "description": description, "agent": self.agent_id}),
            domain_tags=self.domain,
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
