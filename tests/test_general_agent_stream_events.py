"""Tests for DeerFlow event streaming in DeerFlowRuntimeAdapter."""

from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage

from swarmmind.agents.general_agent import DeerFlowRuntimeAdapter, _StreamCaptureState


class FakeStreamingAgent:
    def __init__(self, values_chunks):
        self._values_chunks = values_chunks

    def stream(self, state, config=None, context=None, stream_mode=None):
        assert state["messages"][0].id == "current-turn-user"
        # Emit values-mode chunks tagged with the mode key, matching
        # the dual stream_mode=["messages", "values"] format.
        for chunk in self._values_chunks:
            yield ("values", chunk)

    async def astream(self, state, config=None, context=None, stream_mode=None):
        """Async version of stream."""
        for item in self.stream(state, config, context, stream_mode):
            yield item


class FakeClient:
    def __init__(self, chunks):
        self._agent = FakeStreamingAgent(chunks)

    def _get_runnable_config(
        self,
        thread_id,
        model_name=None,
        thinking_enabled=True,
        plan_mode=False,
        subagent_enabled=False,
    ):
        return {
            "thread_id": thread_id,
            "model_name": model_name,
            "thinking_enabled": thinking_enabled,
            "plan_mode": plan_mode,
            "subagent_enabled": subagent_enabled,
        }

    def _ensure_agent(self, config):
        return None

    def _extract_text(self, content):
        return content if isinstance(content, str) else ""


def test_stream_events_skips_history_messages_before_current_turn(monkeypatch):
    monkeypatch.setattr("swarmmind.agents.general_agent.uuid.uuid4", lambda: "current-turn-user")

    agent = DeerFlowRuntimeAdapter.__new__(DeerFlowRuntimeAdapter)
    agent._client = FakeClient(
        [
            {
                "messages": [
                    HumanMessage(content="上一轮问题", id="history-user"),
                    AIMessage(content="上一轮回答", id="history-assistant"),
                    HumanMessage(content="这一轮问题", id="current-turn-user"),
                ],
            },
            {
                "messages": [
                    HumanMessage(content="上一轮问题", id="history-user"),
                    AIMessage(content="上一轮回答", id="history-assistant"),
                    HumanMessage(content="这一轮问题", id="current-turn-user"),
                    AIMessage(content="这���轮回答", id="current-turn-assistant"),
                ],
            },
        ],
    )
    agent._resolve_runtime_options = lambda runtime_options: SimpleNamespace(
        model_name="test-model",
        thinking_enabled=True,
        plan_mode=False,
        subagent_enabled=False,
    )

    events = list(
        agent.stream_events(
            "这一轮问题",
            ctx=SimpleNamespace(session_id="conversation-1"),
            runtime_options=SimpleNamespace(),
        ),
    )

    # Values-mode only: no messages-mode chunks, so no streaming events;
    # only the values snapshot produces a final_text tracked internally.
    # Since AIMessage has no tool_calls, values handler yields nothing visible.
    assert events == []


def test_process_messages_mode_chunk_accumulates_reasoning_and_content() -> None:
    agent = DeerFlowRuntimeAdapter.__new__(DeerFlowRuntimeAdapter)
    capture_state = _StreamCaptureState()

    first_events = agent._process_messages_mode_chunk(
        AIMessageChunk(
            id="chunk-1",
            content="hello",
            additional_kwargs={"reasoning_content": "step 1"},
        ),
        capture_state,
    )
    second_events = agent._process_messages_mode_chunk(
        AIMessageChunk(
            id="chunk-1",
            content=" world",
            additional_kwargs={"reasoning_content": " + step 2"},
        ),
        capture_state,
    )

    assert first_events == [
        {"type": "assistant_reasoning", "message_id": "chunk-1", "content": "step 1"},
        {"type": "assistant_message", "message_id": "chunk-1", "content": "hello"},
    ]
    assert second_events == [
        {"type": "assistant_reasoning", "message_id": "chunk-1", "content": "step 1 + step 2"},
        {"type": "assistant_message", "message_id": "chunk-1", "content": "hello world"},
    ]
    assert capture_state.accumulated_reasoning == "step 1 + step 2"
    assert capture_state.accumulated_content == "hello world"


def test_process_messages_mode_chunk_resets_accumulators_for_new_message_id() -> None:
    agent = DeerFlowRuntimeAdapter.__new__(DeerFlowRuntimeAdapter)
    capture_state = _StreamCaptureState(
        current_chunk_msg_id="chunk-1",
        accumulated_reasoning="previous reasoning",
        accumulated_content="previous content",
    )

    events = agent._process_messages_mode_chunk(
        AIMessageChunk(
            id="chunk-2",
            content="fresh",
            additional_kwargs={"reasoning_content": "new reasoning"},
        ),
        capture_state,
    )

    assert events == [
        {"type": "assistant_reasoning", "message_id": "chunk-2", "content": "new reasoning"},
        {"type": "assistant_message", "message_id": "chunk-2", "content": "fresh"},
    ]
    assert capture_state.current_chunk_msg_id == "chunk-2"
    assert capture_state.accumulated_reasoning == "new reasoning"
    assert capture_state.accumulated_content == "fresh"


def test_process_custom_mode_chunk_filters_and_normalizes_task_events() -> None:
    assert DeerFlowRuntimeAdapter._process_custom_mode_chunk("ignored") is None
    assert DeerFlowRuntimeAdapter._process_custom_mode_chunk({"type": "other"}) is None
    assert DeerFlowRuntimeAdapter._process_custom_mode_chunk(
        {
            "type": "task_running",
            "task_id": "task-1",
            "description": "desc",
            "message": "working",
        }
    ) == {
        "type": "custom_event",
        "event_type": "task_running",
        "task_id": "task-1",
        "description": "desc",
        "message": "working",
        "result": None,
        "error": None,
    }


def test_iter_new_turn_messages_skips_pre_turn_user_and_seen_messages() -> None:
    history_assistant = AIMessage(content="history", id="history-assistant")
    current_assistant = AIMessage(content="current", id="current-assistant")
    duplicate_tool = ToolMessage(content="done", tool_call_id="call-1", name="lookup", id="tool-1")
    fresh_tool = ToolMessage(content="fresh", tool_call_id="call-2", name="search", id="tool-2")
    seen_ids = {"tool-1"}

    yielded = list(
        DeerFlowRuntimeAdapter._iter_new_turn_messages(
            [
                HumanMessage(content="history user", id="history-user"),
                history_assistant,
                HumanMessage(content="current user", id="current-user"),
                HumanMessage(content="follow-up user", id="other-user"),
                current_assistant,
                duplicate_tool,
                fresh_tool,
            ],
            "current-user",
            seen_ids,
        )
    )

    assert yielded == [current_assistant, fresh_tool]
    assert seen_ids == {"tool-1", "current-assistant", "tool-2"}


def test_process_values_mode_message_emits_tool_calls_and_tracks_final_text() -> None:
    agent = DeerFlowRuntimeAdapter.__new__(DeerFlowRuntimeAdapter)
    agent._client = SimpleNamespace(_extract_text=lambda content: content if isinstance(content, str) else "")
    capture_state = _StreamCaptureState()

    events = agent._process_values_mode_message(
        AIMessage(
            content="final answer",
            id="assistant-1",
            tool_calls=[{"name": "search_docs", "args": {"q": "streaming"}, "id": "call-1"}],
        ),
        capture_state,
    )

    assert events == [
        {
            "type": "assistant_tool_calls",
            "message_id": "assistant-1",
            "tool_calls": [{"name": "search_docs", "args": {"q": "streaming"}, "id": "call-1"}],
        }
    ]
    assert capture_state.final_text == "final answer"


def test_process_values_mode_message_emits_tool_result_and_summarizes_tool_output() -> None:
    agent = DeerFlowRuntimeAdapter.__new__(DeerFlowRuntimeAdapter)
    agent._client = SimpleNamespace(_extract_text=lambda content: content if isinstance(content, str) else "")
    capture_state = _StreamCaptureState()

    events = agent._process_values_mode_message(
        ToolMessage(
            content="tool output",
            tool_call_id="call-1",
            name="search_docs",
            id="tool-1",
        ),
        capture_state,
    )

    assert events == [
        {
            "type": "tool_result",
            "message_id": "tool-1",
            "tool_name": "search_docs",
            "tool_call_id": "call-1",
            "content": "tool output",
        }
    ]
    assert capture_state.tool_results == ["[search_docs]: tool output"]
