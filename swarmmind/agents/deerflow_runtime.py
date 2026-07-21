"""DeerFlowRuntime — SwarmMind's DeerFlow runtime boundary.

Bridges SwarmMind control-plane calls to an embedded DeerFlow runtime instance.
"""

from __future__ import annotations

import importlib
import inspect
import logging
import uuid
from collections.abc import AsyncGenerator, Generator
from functools import cache
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from swarmmind.agents.base import BaseAgent
from swarmmind.agents.middlewares.identity_middleware import SwarmMindIdentityMiddleware
from swarmmind.models import ConversationRuntimeOptions, MemoryContext
from swarmmind.runtime import ensure_default_runtime_instance
from swarmmind.runtime.models import RuntimeInstance
from swarmmind.services.runtime_bridge import iter_async_generator_in_thread, run_coroutine_blocking
from swarmmind.services.runtime_event_processing import (
    StreamCaptureState,
    _streaming_ai_message_event,
    iter_new_turn_messages,
    process_custom_mode_chunk,
    process_messages_mode_chunk,
    process_values_mode_message,
    process_values_mode_state,
    serialize_deerflow_message,
)

logger = logging.getLogger(__name__)


@cache
def _load_deerflow_client_module() -> Any:
    """Import DeerFlow client after SwarmMind has prepared DeerFlow env/config."""
    return importlib.import_module("deerflow.client")


@cache
def _get_swarmmind_deerflow_client_impl() -> type:
    """Build the branded subclass once while preserving DeerFlow's native methods."""
    deerflow_module = _load_deerflow_client_module()

    class _SwarmMindDeerFlowClient(_SwarmMindDeerFlowClientMixin, deerflow_module.DeerFlowClient):
        pass

    return _SwarmMindDeerFlowClient


class _SwarmMindDeerFlowClientMixin:
    """DeerFlow client wrapper that injects SwarmMind product identity."""

    def __init__(self, *args, system_prompt: str, **kwargs) -> None:
        middlewares = [*(kwargs.pop("middlewares", None) or []), SwarmMindIdentityMiddleware(system_prompt)]
        super().__init__(*args, middlewares=middlewares, **kwargs)


class SwarmMindDeerFlowClient:
    """Lazy factory for SwarmMind's DeerFlow client wrapper."""

    def __new__(cls, *args, **kwargs) -> Any:
        """Create the lazily imported native DeerFlow client subclass."""
        return _get_swarmmind_deerflow_client_impl()(*args, **kwargs)


class DeerFlowRuntime(BaseAgent):
    """SwarmMind DeerFlow runtime boundary.

    Uses DeerFlow's full tool ecosystem (web search, file I/O, bash, etc.)
    without routing the chat turn through a SwarmMind ActionProposal gate.
    """

    def __init__(
        self,
        runtime_instance: RuntimeInstance | None = None,
        default_model: str | None = None,
        thinking_enabled: bool = True,
        subagent_enabled: bool = False,
        plan_mode: bool = False,
        middlewares: list | None = None,
    ) -> None:
        # Initialize BaseAgent (sets self.memory, loads system_prompt from DB)
        super().__init__(agent_id="general", domain="general")

        self._runtime_instance = runtime_instance or ensure_default_runtime_instance()
        self._config_path = str(self._runtime_instance.config_path)
        self._default_model = default_model
        self._thinking_enabled = thinking_enabled
        self._subagent_enabled = subagent_enabled
        self._plan_mode = plan_mode

        self._client: Any = SwarmMindDeerFlowClient(
            config_path=self._config_path,
            model_name=default_model,
            thinking_enabled=thinking_enabled,
            subagent_enabled=subagent_enabled,
            plan_mode=plan_mode,
            system_prompt=self._system_prompt,
            middlewares=middlewares or [],
        )

    @property
    def domain_tags(self) -> list[str]:
        """The DeerFlow runtime reads no specific domain tags (catch-all fallback)."""
        return []

    def run_turn(
        self,
        goal: str,
        ctx: MemoryContext | None = None,
        runtime_options: ConversationRuntimeOptions | None = None,
    ) -> str:
        """Execute a DeerFlow turn and return the final text response."""
        logger.info("DeerFlow runtime running goal=%r", goal[:100])

        final_text, _tool_results = self._run_deerflow_turn(
            goal,
            ctx=ctx,
            runtime_options=runtime_options,
        )

        if not final_text:
            logger.warning("DeerFlow returned empty response for goal=%r", goal[:50])
            final_text = "DeerFlow processed the request but returned no text output."

        logger.info("DeerFlow runtime completed: text_length=%d", len(final_text))
        return final_text

    async def _astream_events(
        self,
        goal: str,
        ctx: MemoryContext | None = None,
        runtime_options: ConversationRuntimeOptions | None = None,
        *,
        native_messages: bool = False,
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
                events = process_messages_mode_chunk(msg_chunk, capture_state)
                for event in events:
                    yield event
                if native_messages and events:
                    yield _streaming_ai_message_event(capture_state)

            elif mode_tag == "custom":
                event = process_custom_mode_chunk(chunk)
                if event is not None:
                    yield event

            elif mode_tag == "values":
                for event in process_values_mode_state(chunk, capture_state):
                    yield event
                messages = chunk.get("messages", [])
                for msg in iter_new_turn_messages(messages, current_user_message_id, capture_state.seen_ids):
                    if native_messages:
                        native_message = serialize_deerflow_message(msg, self._client._extract_text)
                        if native_message is not None:
                            yield {"type": "deerflow.message", "message": native_message}
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
        *,
        native_messages: bool = False,
    ) -> Generator[dict[str, Any], None, tuple[str, list[str]]]:
        """Yield structured runtime events for a DeerFlow-backed turn.

        Uses async stream mode internally to properly handle async tools like task_tool.
        This bridges the async _astream_events with the sync generator interface.

        IMPORTANT: Runs async DeerFlow execution inside a dedicated worker thread
        with its own event loop. This isolates the runtime from any existing loop
        in the caller while preserving the synchronous generator API.
        """
        async_kwargs: dict[str, Any] = {
            "ctx": ctx,
            "runtime_options": runtime_options,
        }
        if "native_messages" in inspect.signature(self._astream_events).parameters:
            async_kwargs["native_messages"] = native_messages

        yield from iter_async_generator_in_thread(
            lambda: self._astream_events(goal, **async_kwargs),
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
