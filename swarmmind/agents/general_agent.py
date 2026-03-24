"""GeneralAgent — Default DeerFlow-powered agent for unclassified goals.

Handles any goal that doesn't match a specialized agent.
Uses DeerFlow's full tool ecosystem (web search, file I/O, bash, etc.)
"""

import json
import logging

from swarmmind.agents.base import BaseAgent

# DeerFlow event types (from deerflow-core/src/deerflow-core/logging_handler.py)
_DEERFLOW_EVENT_MESSAGES = "messages-tuple"
_DEERFLOW_MSG_AI = "ai"
_DEERFLOW_MSG_TOOL = "tool"
_DEERFLOW_EVENT_END = "end"
from swarmmind.config import DEER_FLOW_CONFIG_PATH
from swarmmind.context_broker import update_proposal_result
from swarmmind.db import get_connection
from swarmmind.models import ActionProposal, MemoryContext

logger = logging.getLogger(__name__)


class GeneralAgent(BaseAgent):
    """Default agent wrapping DeerFlowClient.

    Handles any goal that doesn't match a specialized agent.
    Uses DeerFlow's full tool ecosystem (web search, file I/O, bash, etc.)
    Inherits from BaseAgent to reuse _resolve_write_scope, memory, and initialization.
    """

    def __init__(
        self,
        deer_flow_config_path: str | None = None,
        default_model: str | None = None,
        thinking_enabled: bool = True,
    ):
        # Initialize BaseAgent (sets self.memory, loads system_prompt from DB)
        super().__init__(agent_id="general", domain="general")

        self._config_path = deer_flow_config_path or DEER_FLOW_CONFIG_PATH
        self._default_model = default_model
        self._thinking_enabled = thinking_enabled

        if self._config_path is None:
            raise ValueError(
                "DeerFlow is not configured. "
                "To enable GeneralAgent, set DEER_FLOW_CONFIG_PATH environment variable "
                "to point to your DeerFlow config.yaml, and install with "
                "`uv sync --extra deerflow`."
            )

        try:
            from deerflow.client import DeerFlowClient
        except ImportError:
            raise ValueError(
                "DeerFlow is not installed. "
                "Install it with `uv sync --extra deerflow` to enable GeneralAgent."
            )

        self._client = DeerFlowClient(
            config_path=self._config_path,
            model_name=default_model,
            thinking_enabled=thinking_enabled,
        )

    def act(
        self,
        goal: str,
        action_proposal_id: str,
        ctx: MemoryContext | None = None,
    ) -> ActionProposal:
        """Execute a goal using DeerFlow and update the proposal.

        Uses DeerFlow's stream() to execute the goal, collects the final
        text response, updates the proposal, and writes results to memory.
        """
        logger.info(
            "GeneralAgent acting on goal=%r proposal_id=%s",
            goal[:100], action_proposal_id,
        )

        thread_id = ctx.session_id if ctx else None
        final_text = ""
        tool_results: list[str] = []

        try:
            for event in self._client.stream(goal, thread_id=thread_id):
                if event.type == _DEERFLOW_EVENT_MESSAGES:
                    data = event.data
                    msg_type = data.get("type", "")
                    if msg_type == _DEERFLOW_MSG_AI:
                        content = data.get("content", "")
                        if content:
                            final_text = content
                    elif msg_type == _DEERFLOW_MSG_TOOL:
                        tool_name = data.get("name", "unknown")
                        tool_content = data.get("content", "")
                        tool_results.append(f"[{tool_name}]: {tool_content[:200]}")
                elif event.type == _DEERFLOW_EVENT_END:
                    pass
        except Exception as e:
            logger.error("DeerFlow stream error: %s", e)
            self._create_rejected_proposal(
                action_proposal_id,
                f"GeneralAgent DeerFlow error: {e}",
            )
            raise

        if not final_text:
            logger.warning("DeerFlow returned empty response for goal=%r", goal[:50])
            final_text = "DeerFlow processed the request but returned no text output."

        # Build a description from the final text (truncated for DB)
        if len(final_text) > 1000:
            description = final_text[:997] + "..."
        else:
            description = final_text

        # Update proposal with result
        update_proposal_result(
            proposal_id=action_proposal_id,
            description=description,
            target_resource=None,
            confidence=0.8,
        )

        # Write goal + result to layered memory
        scope = self._resolve_write_scope(ctx)
        self.memory.write(
            scope=scope,
            key=f"goal:{action_proposal_id}",
            value=json.dumps({
                "goal": goal,
                "result": final_text[:2000],
                "agent": self.agent_id,
                "tool_calls": len(tool_results),
            }),
            tags=[self.domain],
        )

        # Also write tool results summary if any
        if tool_results:
            self.memory.write(
                scope=scope,
                key=f"tools:{action_proposal_id}",
                value=json.dumps({
                    "tool_count": len(tool_results),
                    "summary": "; ".join(tool_results[:5]),
                }),
                tags=[self.domain, "tools"],
            )

        logger.info(
            "GeneralAgent completed: proposal_id=%s text_length=%d",
            action_proposal_id, len(final_text),
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
