"""GeneralAgent — Default DeerFlow-powered agent for unclassified goals.

Handles any goal that doesn't match a specialized agent.
Uses DeerFlow's full tool ecosystem (web search, file I/O, bash, etc.)
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Generator
from typing import Any

from deerflow.client import DeerFlowClient
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from swarmmind.agents.base import BaseAgent
from swarmmind.config import DEER_FLOW_CONFIG_PATH
from swarmmind.context_broker import update_proposal_result
from swarmmind.db import get_connection
from swarmmind.models import ActionProposal, ConversationRuntimeOptions, MemoryContext

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
        subagent_enabled: bool = False,
        plan_mode: bool = False,
    ):
        # Initialize BaseAgent (sets self.memory, loads system_prompt from DB)
        super().__init__(agent_id="general", domain="general")

        self._config_path = deer_flow_config_path or DEER_FLOW_CONFIG_PATH
        self._default_model = default_model
        self._thinking_enabled = thinking_enabled
        self._subagent_enabled = subagent_enabled
        self._plan_mode = plan_mode

        self._client: DeerFlowClient = DeerFlowClient(
            config_path=self._config_path,
            model_name=default_model,
            thinking_enabled=thinking_enabled,
            subagent_enabled=subagent_enabled,
            plan_mode=plan_mode,
        )

    @property
    def domain_tags(self) -> list[str]:
        """GeneralAgent reads no specific domain tags (catch-all fallback)."""
        return []

    def act(
        self,
        goal: str,
        action_proposal_id: str,
        ctx: MemoryContext | None = None,
        runtime_options: ConversationRuntimeOptions | None = None,
    ) -> ActionProposal:
        """Execute a goal using DeerFlow and update the proposal.

        Uses DeerFlow's stream() to execute the goal, collects the final
        text response, updates the proposal, and writes results to memory.
        """
        logger.info(
            "GeneralAgent acting on goal=%r proposal_id=%s",
            goal[:100], action_proposal_id,
        )

        try:
            final_text, tool_results = self._run_deerflow_turn(
                goal,
                ctx=ctx,
                runtime_options=runtime_options,
            )
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

    def stream_events(
        self,
        goal: str,
        ctx: MemoryContext | None = None,
        runtime_options: ConversationRuntimeOptions | None = None,
    ) -> Generator[dict[str, Any], None, tuple[str, list[str]]]:
        """Yield structured runtime events for a DeerFlow-backed turn.

        SwarmMind's temporary ChatSession uses this to surface runtime state
        without exposing DeerFlow's raw internal terms directly to the user.
        """
        thread_id = ctx.session_id if ctx and ctx.session_id else str(uuid.uuid4())
        effective_runtime = self._resolve_runtime_options(runtime_options)
        config = self._client._get_runnable_config(
            thread_id,
            model_name=effective_runtime.model_name,
            thinking_enabled=effective_runtime.thinking_enabled,
            plan_mode=effective_runtime.plan_mode,
            subagent_enabled=effective_runtime.subagent_enabled,
        )
        self._client._ensure_agent(config)

        state: dict[str, Any] = {"messages": [HumanMessage(content=goal)]}
        runtime_context = {"thread_id": thread_id}

        seen_ids: set[str] = set()
        final_text = ""
        tool_results: list[str] = []

        for chunk in self._client._agent.stream(
            state,
            config=config,
            context=runtime_context,
            stream_mode="values",
        ):
            messages = chunk.get("messages", [])

            for msg in messages:
                msg_id = getattr(msg, "id", None)
                if msg_id and msg_id in seen_ids:
                    continue
                if msg_id:
                    seen_ids.add(msg_id)

                if isinstance(msg, AIMessage):
                    reasoning = self._extract_reasoning(msg)
                    if reasoning:
                        yield {
                            "type": "assistant_reasoning",
                            "message_id": msg_id,
                            "content": reasoning,
                        }

                    if msg.tool_calls:
                        yield {
                            "type": "assistant_tool_calls",
                            "message_id": msg_id,
                            "tool_calls": [
                                {
                                    "name": tool_call.get("name"),
                                    "args": tool_call.get("args", {}),
                                    "id": tool_call.get("id"),
                                }
                                for tool_call in msg.tool_calls
                            ],
                        }

                    content = self._client._extract_text(msg.content)
                    if content:
                        final_text = content
                        yield {
                            "type": "assistant_message",
                            "message_id": msg_id,
                            "content": content,
                        }

                elif isinstance(msg, ToolMessage):
                    tool_name = getattr(msg, "name", None) or "unknown"
                    tool_content = self._client._extract_text(msg.content)
                    if tool_content:
                        tool_results.append(f"[{tool_name}]: {tool_content[:200]}")

                    yield {
                        "type": "tool_result",
                        "message_id": msg_id,
                        "tool_name": tool_name,
                        "tool_call_id": getattr(msg, "tool_call_id", None),
                        "content": tool_content,
                    }

        return final_text, tool_results

    def _run_deerflow_turn(
        self,
        goal: str,
        ctx: MemoryContext | None = None,
        runtime_options: ConversationRuntimeOptions | None = None,
    ) -> tuple[str, list[str]]:
        final_text = ""
        tool_results: list[str] = []

        stream = self.stream_events(goal, ctx=ctx, runtime_options=runtime_options)
        while True:
            try:
                next(stream)
            except StopIteration as stop:
                final_text, tool_results = stop.value
                break

        return final_text, tool_results

    def _resolve_runtime_options(
        self,
        runtime_options: ConversationRuntimeOptions | None = None,
    ) -> ConversationRuntimeOptions:
        if runtime_options is not None:
            return runtime_options

        return ConversationRuntimeOptions(
            mode="thinking" if self._thinking_enabled else "flash",
            model_name=self._default_model,
            thinking_enabled=self._thinking_enabled,
            plan_mode=self._plan_mode,
            subagent_enabled=self._subagent_enabled,
        )

    @staticmethod
    def _extract_reasoning(message: AIMessage) -> str | None:
        additional_kwargs = getattr(message, "additional_kwargs", None) or {}
        reasoning = additional_kwargs.get("reasoning_content")
        if isinstance(reasoning, str) and reasoning.strip():
            return reasoning.strip()

        content = getattr(message, "content", None)
        if isinstance(content, list):
            reasoning_parts: list[str] = []
            for block in content:
                if isinstance(block, dict):
                    block_type = block.get("type")
                    if block_type == "thinking" and isinstance(block.get("thinking"), str):
                        thinking = block.get("thinking", "").strip()
                        if thinking:
                            reasoning_parts.append(thinking)
            if reasoning_parts:
                return "\n\n".join(reasoning_parts)

        return None
