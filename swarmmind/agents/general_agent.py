"""DeerFlowRuntimeAdapter — SwarmMind's DeerFlow runtime adapter.

Bridges SwarmMind control-plane calls to an embedded DeerFlow runtime instance.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncGenerator, Generator
from typing import Any

import deerflow.client as deerflow_client_module
from deerflow.client import DeerFlowClient, StreamEvent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from swarmmind.agents.base import BaseAgent
from swarmmind.context_broker import update_proposal_result
from swarmmind.models import ActionProposal, ConversationRuntimeOptions, MemoryContext
from swarmmind.prompting import rewrite_swarmmind_identity_prompt
from swarmmind.runtime import RuntimeExecutionError, ensure_default_runtime_instance
from swarmmind.runtime.models import RuntimeInstance
from swarmmind.services.runtime_bridge import iter_async_generator_in_thread, run_coroutine_blocking
from swarmmind.services.runtime_event_processing import (
    StreamCaptureState,
    iter_new_turn_messages,
    process_custom_mode_chunk,
    process_messages_mode_chunk,
    process_values_mode_message,
)

logger = logging.getLogger(__name__)


class SwarmMindDeerFlowClient(DeerFlowClient):
    """DeerFlow client wrapper that injects SwarmMind product identity."""

    def __init__(self, *args, system_prompt: str, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._swarmmind_system_prompt = system_prompt
        # Note: ClarificationMiddleware is already added by DeerFlow's _build_middlewares
        # No need to add it again here to avoid duplicates

    async def astream(
        self,
        message: str,
        *,
        thread_id: str | None = None,
        **kwargs,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Async streaming version that properly handles async tools like task_tool.

        This is needed because the sync stream() method cannot execute async tools
        (they require ainvoke/ainvoke which only works in async context).
        """
        if thread_id is None:
            thread_id = str(uuid.uuid4())

        config = self._get_runnable_config(thread_id, **kwargs)
        self._ensure_agent(config)

        state: dict[str, Any] = {"messages": [HumanMessage(content=message)]}
        context = {"thread_id": thread_id}
        if self._agent_name:
            context["agent_name"] = self._agent_name

        seen_ids: set[str] = set()
        cumulative_usage: dict[str, int] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }

        async for chunk in self._agent.astream(state, config=config, context=context, stream_mode="values"):
            messages = chunk.get("messages", [])

            for msg in messages:
                msg_id = getattr(msg, "id", None)
                if msg_id and msg_id in seen_ids:
                    continue
                if msg_id:
                    seen_ids.add(msg_id)

                if isinstance(msg, AIMessage):
                    # Track token usage from AI messages
                    usage = getattr(msg, "usage_metadata", None)
                    if usage:
                        cumulative_usage["input_tokens"] += usage.get("input_tokens", 0) or 0
                        cumulative_usage["output_tokens"] += usage.get("output_tokens", 0) or 0
                        cumulative_usage["total_tokens"] += usage.get("total_tokens", 0) or 0

                    if msg.tool_calls:
                        yield StreamEvent(
                            type="messages-tuple",
                            data={
                                "type": "ai",
                                "content": "",
                                "id": msg_id,
                                "tool_calls": [
                                    {"name": tc["name"], "args": tc["args"], "id": tc.get("id")}
                                    for tc in msg.tool_calls
                                ],
                            },
                        )

                    text = self._extract_text(msg.content)
                    if text:
                        event_data: dict[str, Any] = {"type": "ai", "content": text, "id": msg_id}
                        if usage:
                            event_data["usage_metadata"] = {
                                "input_tokens": usage.get("input_tokens", 0) or 0,
                                "output_tokens": usage.get("output_tokens", 0) or 0,
                                "total_tokens": usage.get("total_tokens", 0) or 0,
                            }
                        yield StreamEvent(type="messages-tuple", data=event_data)

                elif isinstance(msg, ToolMessage):
                    yield StreamEvent(
                        type="messages-tuple",
                        data={
                            "type": "tool",
                            "content": self._extract_text(msg.content),
                            "name": getattr(msg, "name", None),
                            "tool_call_id": getattr(msg, "tool_call_id", None),
                            "id": msg_id,
                        },
                    )

            # Emit a values event for each state snapshot
            yield StreamEvent(
                type="values",
                data={
                    "title": chunk.get("title"),
                    "messages": [self._serialize_message(m) for m in messages],
                    "artifacts": chunk.get("artifacts", []),
                },
            )

        yield StreamEvent(type="end", data={"usage": cumulative_usage})

    def _ensure_agent(self, config):
        """Create the underlying DeerFlow agent with SwarmMind branding."""
        cfg = config.get("configurable", {})
        key = (
            cfg.get("model_name"),
            cfg.get("thinking_enabled"),
            cfg.get("is_plan_mode"),
            cfg.get("subagent_enabled"),
        )

        logger.info(
            "[DEBUG] _ensure_agent called: subagent_enabled=%s, cfg=%s",
            cfg.get("subagent_enabled"),
            cfg,
        )

        if self._agent is not None and self._agent_config_key == key:
            logger.info("[DEBUG] Using cached agent")
            return

        thinking_enabled = cfg.get("thinking_enabled", True)
        model_name = cfg.get("model_name")
        subagent_enabled = cfg.get("subagent_enabled", False)
        max_concurrent_subagents = cfg.get("max_concurrent_subagents", 3)
        logger.info("[DEBUG] Creating new agent: subagent_enabled=%s", subagent_enabled)

        logger.info("[DEBUG] apply_prompt_template: subagent_enabled=%s", subagent_enabled)
        base_prompt = deerflow_client_module.apply_prompt_template(
            subagent_enabled=subagent_enabled,
            max_concurrent_subagents=max_concurrent_subagents,
            agent_name=self._agent_name,
        )
        system_prompt = rewrite_swarmmind_identity_prompt(base_prompt, self._swarmmind_system_prompt)

        # Get tools with subagent support if enabled
        tools = self._get_tools(model_name=model_name, subagent_enabled=subagent_enabled)
        logger.info("Tools loaded: count=%d, subagent_enabled=%s", len(tools), subagent_enabled)
        if subagent_enabled:
            tool_names = [t.name if hasattr(t, "name") else str(t) for t in tools]
            logger.info("Available tools: %s", tool_names)

        kwargs: dict[str, Any] = {
            "model": deerflow_client_module.create_chat_model(name=model_name, thinking_enabled=thinking_enabled),
            "tools": tools,
            "middleware": deerflow_client_module._build_middlewares(
                config,
                model_name=model_name,
                agent_name=self._agent_name,
                custom_middlewares=self._middlewares,
            ),
            "system_prompt": system_prompt,
            "state_schema": deerflow_client_module.ThreadState,
        }
        checkpointer = self._checkpointer
        if checkpointer is None:
            from deerflow.agents.checkpointer import get_checkpointer

            checkpointer = get_checkpointer()
        if checkpointer is not None:
            kwargs["checkpointer"] = checkpointer

        self._agent = deerflow_client_module.create_agent(**kwargs)
        self._agent_config_key = key
        logger.info(
            "SwarmMind agent created: agent_name=%s, model=%s, thinking=%s",
            self._agent_name,
            model_name,
            thinking_enabled,
        )


class DeerFlowRuntimeAdapter(BaseAgent):
    """SwarmMind adapter around DeerFlowClient.

    Handles any goal that doesn't match a specialized agent.
    Uses DeerFlow's full tool ecosystem (web search, file I/O, bash, etc.)
    Inherits from BaseAgent to reuse _resolve_write_scope, memory, and initialization.
    """

    def __init__(
        self,
        runtime_instance: RuntimeInstance | None = None,
        default_model: str | None = None,
        thinking_enabled: bool = True,
        subagent_enabled: bool = False,
        plan_mode: bool = False,
    ) -> None:
        # Initialize BaseAgent (sets self.memory, loads system_prompt from DB)
        super().__init__(agent_id="general", domain="general")

        self._runtime_instance = runtime_instance or ensure_default_runtime_instance()
        self._config_path = str(self._runtime_instance.config_path)
        self._default_model = default_model
        self._thinking_enabled = thinking_enabled
        self._subagent_enabled = subagent_enabled
        self._plan_mode = plan_mode

        self._client: DeerFlowClient = SwarmMindDeerFlowClient(
            config_path=self._config_path,
            model_name=default_model,
            thinking_enabled=thinking_enabled,
            subagent_enabled=subagent_enabled,
            plan_mode=plan_mode,
            system_prompt=self._system_prompt,
        )

    @property
    def domain_tags(self) -> list[str]:
        """The runtime adapter reads no specific domain tags (catch-all fallback)."""
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
            "DeerFlowRuntimeAdapter acting on goal=%r proposal_id=%s",
            goal[:100],
            action_proposal_id,
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
                f"DeerFlowRuntimeAdapter error: {e}",
            )
            raise RuntimeExecutionError(str(e)) from e

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
            value=json.dumps(
                {
                    "goal": goal,
                    "result": final_text[:2000],
                    "agent": self.agent_id,
                    "tool_calls": len(tool_results),
                }
            ),
            tags=[self.domain],
        )

        # Also write tool results summary if any
        if tool_results:
            self.memory.write(
                scope=scope,
                key=f"tools:{action_proposal_id}",
                value=json.dumps(
                    {
                        "tool_count": len(tool_results),
                        "summary": "; ".join(tool_results[:5]),
                    }
                ),
                tags=[self.domain, "tools"],
            )

        logger.info(
            "DeerFlowRuntimeAdapter completed: proposal_id=%s text_length=%d",
            action_proposal_id,
            len(final_text),
        )

        # Return updated proposal
        from swarmmind.repositories.action_proposal import ActionProposalRepository

        proposal = ActionProposalRepository().get(action_proposal_id)
        if proposal is None:
            raise RuntimeError(f"Action proposal {action_proposal_id} not found after update")
        return proposal

    async def _astream_events(
        self,
        goal: str,
        ctx: MemoryContext | None = None,
        runtime_options: ConversationRuntimeOptions | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Async version: Yield structured runtime events for a DeerFlow-backed turn.

        Uses async stream mode to properly handle async tools like task_tool.
        """
        thread_id = ctx.session_id if ctx and ctx.session_id else str(uuid.uuid4())
        effective_runtime = self._resolve_runtime_options(runtime_options)
        logger.info("[DEBUG] astream_events: subagent_enabled=%s", effective_runtime.subagent_enabled)
        config = self._client._get_runnable_config(
            thread_id,
            model_name=effective_runtime.model_name,
            thinking_enabled=effective_runtime.thinking_enabled,
            plan_mode=effective_runtime.plan_mode,
            subagent_enabled=effective_runtime.subagent_enabled,
        )
        logger.info("[DEBUG] astream_events: config configurable=%s", config.get("configurable"))
        self._client._ensure_agent(config)

        current_user_message_id = str(uuid.uuid4())
        state: dict[str, Any] = {"messages": [HumanMessage(content=goal, id=current_user_message_id)]}
        runtime_context = {"thread_id": thread_id}

        capture_state = StreamCaptureState()

        async for mode_tag, chunk in self._client._agent.astream(
            state,
            config=config,
            context=runtime_context,
            stream_mode=["messages", "values", "custom"],
        ):
            if mode_tag == "messages":
                msg_chunk, _metadata = chunk
                for event in process_messages_mode_chunk(msg_chunk, capture_state):
                    yield event

            elif mode_tag == "custom":
                event = process_custom_mode_chunk(chunk)
                if event is not None:
                    yield event

            elif mode_tag == "values":
                messages = chunk.get("messages", [])
                for msg in iter_new_turn_messages(messages, current_user_message_id, capture_state.seen_ids):
                    for event in process_values_mode_message(msg, capture_state, self._client._extract_text):
                        yield event

        # Fallback: if messages mode captured content but values mode didn't
        if not capture_state.final_text and capture_state.accumulated_content:
            capture_state.final_text = capture_state.accumulated_content

        # Store results for the caller to retrieve
        self._last_final_text = capture_state.final_text
        self._last_tool_results = capture_state.tool_results

    def stream_events(
        self,
        goal: str,
        ctx: MemoryContext | None = None,
        runtime_options: ConversationRuntimeOptions | None = None,
    ) -> Generator[dict[str, Any], None, tuple[str, list[str]]]:
        """Yield structured runtime events for a DeerFlow-backed turn.

        Uses async stream mode internally to properly handle async tools like task_tool.
        This bridges the async _astream_events with the sync generator interface.

        IMPORTANT: Runs async DeerFlow execution inside a dedicated worker thread
        with its own event loop. This isolates the runtime from any existing loop
        in the caller while preserving the synchronous generator API.
        """
        yield from iter_async_generator_in_thread(
            lambda: self._astream_events(goal, ctx=ctx, runtime_options=runtime_options),
            thread_name="deerflow-stream",
            join_timeout=5.0,
            bridge_logger=logger,
        )

        return self._last_final_text, self._last_tool_results

    def _run_deerflow_turn(
        self,
        goal: str,
        ctx: MemoryContext | None = None,
        runtime_options: ConversationRuntimeOptions | None = None,
    ) -> tuple[str, list[str]]:
        return run_coroutine_blocking(
            lambda: self._acollect_turn(goal, ctx=ctx, runtime_options=runtime_options),
            thread_name="deerflow-act",
            join_timeout=5.0,
            bridge_logger=logger,
        )

    async def _acollect_turn(
        self,
        goal: str,
        ctx: MemoryContext | None = None,
        runtime_options: ConversationRuntimeOptions | None = None,
    ) -> tuple[str, list[str]]:
        async for _ in self._astream_events(goal, ctx=ctx, runtime_options=runtime_options):
            pass
        return self._last_final_text, self._last_tool_results

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

# Backward-compatible alias retained while call sites migrate away from the
# misleading "GeneralAgent" name.
GeneralAgent = DeerFlowRuntimeAdapter
