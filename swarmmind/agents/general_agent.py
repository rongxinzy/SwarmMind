"""DeerFlowRuntimeAdapter — SwarmMind's DeerFlow runtime adapter.

Bridges SwarmMind control-plane calls to an embedded DeerFlow runtime instance.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator, Generator
from typing import Any

import deerflow.client as deerflow_client_module
from deerflow.client import DeerFlowClient, StreamEvent
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage

from swarmmind.agents.base import BaseAgent
from swarmmind.context_broker import update_proposal_result
from swarmmind.models import ActionProposal, ConversationRuntimeOptions, MemoryContext
from swarmmind.prompting import rewrite_swarmmind_identity_prompt
from swarmmind.runtime import RuntimeExecutionError, ensure_default_runtime_instance
from swarmmind.runtime.models import RuntimeInstance

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

        seen_ids: set[str] = set()
        final_text = ""
        tool_results: list[str] = []

        # Token-level streaming accumulators (reset per LLM invocation)
        current_chunk_msg_id: str | None = None
        accumulated_reasoning = ""
        accumulated_content = ""

        async for mode_tag, chunk in self._client._agent.astream(
            state,
            config=config,
            context=runtime_context,
            stream_mode=["messages", "values", "custom"],
        ):
            if mode_tag == "messages":
                msg_chunk, _metadata = chunk
                if not isinstance(msg_chunk, AIMessageChunk):
                    continue

                chunk_id = getattr(msg_chunk, "id", None)
                if chunk_id and chunk_id != current_chunk_msg_id:
                    # New LLM invocation started; reset accumulators
                    current_chunk_msg_id = chunk_id
                    accumulated_reasoning = ""
                    accumulated_content = ""

                if not current_chunk_msg_id:
                    current_chunk_msg_id = str(uuid.uuid4())

                # Stream reasoning tokens
                reasoning_delta = self._extract_reasoning_delta(msg_chunk)
                if reasoning_delta:
                    accumulated_reasoning += reasoning_delta
                    yield {
                        "type": "assistant_reasoning",
                        "message_id": current_chunk_msg_id,
                        "content": accumulated_reasoning,
                    }

                # Stream content tokens
                content_delta = self._extract_content_delta(msg_chunk)
                if content_delta:
                    accumulated_content += content_delta
                    yield {
                        "type": "assistant_message",
                        "message_id": current_chunk_msg_id,
                        "content": accumulated_content,
                    }

            elif mode_tag == "custom":
                # Handle custom events from task_tool (task_started, task_running, task_completed, task_failed)
                event = chunk
                logger.debug("Custom event received: %s", event)
                if isinstance(event, dict) and event.get("type") in (
                    "task_started",
                    "task_running",
                    "task_completed",
                    "task_failed",
                ):
                    logger.info("Task event: type=%s, task_id=%s", event.get("type"), event.get("task_id"))
                    yield {
                        "type": "custom_event",
                        "event_type": event["type"],
                        "task_id": event.get("task_id"),
                        "description": event.get("description"),
                        "message": event.get("message"),
                        "result": event.get("result"),
                        "error": event.get("error"),
                    }

            elif mode_tag == "values":
                messages = chunk.get("messages", [])
                turn_anchor_index = next(
                    (
                        index
                        for index, message in enumerate(messages)
                        if isinstance(message, HumanMessage) and getattr(message, "id", None) == current_user_message_id
                    ),
                    -1,
                )

                if turn_anchor_index == -1:
                    continue

                for msg in messages[turn_anchor_index + 1 :]:
                    if isinstance(msg, HumanMessage):
                        continue

                    msg_id = getattr(msg, "id", None)
                    if msg_id and msg_id in seen_ids:
                        continue
                    if msg_id:
                        seen_ids.add(msg_id)

                    if isinstance(msg, AIMessage):
                        # Tool calls (only from values mode for completeness)
                        if msg.tool_calls:
                            tool_names = [tc.get("name") for tc in msg.tool_calls]
                            logger.info("AI tool calls: %s", tool_names)
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

                        # Track final text from complete messages
                        content = self._client._extract_text(msg.content)
                        if content:
                            final_text = content

                    elif isinstance(msg, ToolMessage):
                        tool_name = getattr(msg, "name", None) or "unknown"
                        tool_content = self._client._extract_text(msg.content)
                        logger.info(
                            "Tool result: name=%s, content_preview=%s",
                            tool_name,
                            tool_content[:100] if tool_content else "(empty)",
                        )
                        if tool_content:
                            tool_results.append(f"[{tool_name}]: {tool_content[:200]}")

                        yield {
                            "type": "tool_result",
                            "message_id": msg_id,
                            "tool_name": tool_name,
                            "tool_call_id": getattr(msg, "tool_call_id", None),
                            "content": tool_content,
                        }

        # Fallback: if messages mode captured content but values mode didn't
        if not final_text and accumulated_content:
            final_text = accumulated_content

        # Store results for the caller to retrieve
        self._last_final_text = final_text
        self._last_tool_results = tool_results

    def stream_events(
        self,
        goal: str,
        ctx: MemoryContext | None = None,
        runtime_options: ConversationRuntimeOptions | None = None,
    ) -> Generator[dict[str, Any], None, tuple[str, list[str]]]:
        """Yield structured runtime events for a DeerFlow-backed turn.

        Uses async stream mode internally to properly handle async tools like task_tool.
        This bridges the async _astream_events with the sync generator interface.

        IMPORTANT: Runs async code in the main thread's event loop to prevent httpx
        client binding issues. Subagents create their own event loops in threads,
        which can cause conflicts if the main client is bound to a different loop.
        """
        import queue
        import threading

        result_queue: queue.Queue = queue.Queue()
        exception_container = []
        stop_event = threading.Event()

        async def _run_async_stream():
            """Run the async stream and put events into the queue."""
            try:
                async for event in self._astream_events(goal, ctx=ctx, runtime_options=runtime_options):
                    result_queue.put(("event", event))
            except Exception as e:
                exception_container.append(e)
            finally:
                result_queue.put(("done", None))
                stop_event.set()

        def _run_in_thread():
            """Run the async code in a new event loop in a separate thread.

            NOTE: We create a new event loop in this thread to isolate the
            DeerFlow agent execution from any existing event loop. This is
            necessary because subagents also create their own event loops,
            and we need to avoid httpx client binding conflicts.
            """
            # Set the event loop policy to create new loops per-thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_run_async_stream())
            finally:
                # Clean up any remaining tasks
                try:
                    pending = asyncio.all_tasks(loop)
                    if pending:
                        for task in pending:
                            task.cancel()
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                except Exception:  # nosec: B110 - cleanup code, safe to ignore
                    pass
                loop.close()

        # Start the async execution in a separate thread
        thread = threading.Thread(target=_run_in_thread, name="deerflow-stream")
        thread.start()

        # Yield events as they become available
        try:
            while not stop_event.is_set() or not result_queue.empty():
                try:
                    item_type, event = result_queue.get(timeout=0.1)
                    if item_type == "done":
                        break
                    if item_type == "event":
                        yield event
                except queue.Empty:
                    continue
        finally:
            thread.join(timeout=5.0)
            if thread.is_alive():
                logger.warning("Stream thread did not terminate within timeout")

        # Re-raise any exception from the async execution
        if exception_container:
            raise exception_container[0]

        return self._last_final_text, self._last_tool_results

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

    @staticmethod
    def _extract_reasoning_delta(chunk: AIMessageChunk) -> str | None:
        """Extract incremental reasoning content from a streaming chunk."""
        additional_kwargs = getattr(chunk, "additional_kwargs", None) or {}
        reasoning = additional_kwargs.get("reasoning_content")
        if isinstance(reasoning, str) and reasoning:
            return reasoning

        content = getattr(chunk, "content", None)
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "thinking":
                    thinking = block.get("thinking", "")
                    if thinking:
                        return thinking

        return None

    @staticmethod
    def _extract_content_delta(chunk: AIMessageChunk) -> str | None:
        """Extract incremental text content from a streaming chunk."""
        content = getattr(chunk, "content", None)
        if isinstance(content, str) and content:
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    if text:
                        parts.append(text)
            return "".join(parts) if parts else None
        return None


# Backward-compatible alias retained while call sites migrate away from the
# misleading "GeneralAgent" name.
GeneralAgent = DeerFlowRuntimeAdapter
