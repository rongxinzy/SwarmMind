"""Regression tests for the sync/async stream bridge in DeerFlowRuntimeAdapter."""

from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import AIMessage, AIMessageChunk

from swarmmind.agents.general_agent import DeerFlowRuntimeAdapter
from swarmmind.services.runtime_event_processing import extract_content_delta, extract_reasoning_delta


def test_stream_events_yields_async_events_and_returns_final_result() -> None:
    agent = DeerFlowRuntimeAdapter.__new__(DeerFlowRuntimeAdapter)

    async def fake_astream_events(goal, ctx=None, runtime_options=None):
        assert goal == "investigate"
        assert ctx.session_id == "conv-1"
        yield {"type": "assistant_message", "content": "partial"}
        agent._last_final_text = "final answer"
        agent._last_tool_results = ["tool:done"]

    agent._astream_events = fake_astream_events

    stream = agent.stream_events(
        "investigate", ctx=SimpleNamespace(session_id="conv-1"), runtime_options=SimpleNamespace()
    )
    events: list[dict] = []
    while True:
        try:
            events.append(next(stream))
        except StopIteration as stop:
            final_text, tool_results = stop.value
            break

    assert events == [{"type": "assistant_message", "content": "partial"}]
    assert final_text == "final answer"
    assert tool_results == ["tool:done"]


def test_stream_events_reraises_async_failure() -> None:
    agent = DeerFlowRuntimeAdapter.__new__(DeerFlowRuntimeAdapter)

    async def fake_astream_events(goal, ctx=None, runtime_options=None):
        raise RuntimeError("stream exploded")
        yield  # pragma: no cover

    agent._astream_events = fake_astream_events

    stream = agent.stream_events(
        "investigate", ctx=SimpleNamespace(session_id="conv-1"), runtime_options=SimpleNamespace()
    )

    try:
        next(stream)
    except RuntimeError as exc:
        assert str(exc) == "stream exploded"
    else:  # pragma: no cover
        raise AssertionError("RuntimeError was not re-raised")


def test_run_deerflow_turn_collects_async_result_without_stream_wrapper() -> None:
    agent = DeerFlowRuntimeAdapter.__new__(DeerFlowRuntimeAdapter)

    async def fake_astream_events(goal, ctx=None, runtime_options=None):
        assert goal == "investigate"
        assert ctx.session_id == "conv-1"
        yield {"type": "assistant_message", "content": "partial"}
        agent._last_final_text = "final answer"
        agent._last_tool_results = ["tool:done"]

    agent._astream_events = fake_astream_events

    final_text, tool_results = agent._run_deerflow_turn(
        "investigate",
        ctx=SimpleNamespace(session_id="conv-1"),
        runtime_options=SimpleNamespace(),
    )

    assert final_text == "final answer"
    assert tool_results == ["tool:done"]


def test_extract_reasoning_delta_prefers_additional_kwargs() -> None:
    chunk = AIMessageChunk(content="", additional_kwargs={"reasoning_content": "step by step"})

    assert extract_reasoning_delta(chunk) == "step by step"


def test_extract_reasoning_delta_falls_back_to_thinking_blocks() -> None:
    chunk = AIMessageChunk(content=[{"type": "thinking", "thinking": "consider option A"}])

    assert extract_reasoning_delta(chunk) == "consider option A"


def test_extract_content_delta_handles_text_blocks() -> None:
    chunk = AIMessageChunk(content=[{"type": "text", "text": "hello"}, {"type": "text", "text": " world"}])

    assert extract_content_delta(chunk) == "hello world"


def test_extract_reasoning_collects_multiple_blocks() -> None:
    message = AIMessage(
        content=[
            {"type": "thinking", "thinking": "first pass"},
            {"type": "thinking", "thinking": "second pass"},
        ]
    )

    assert DeerFlowRuntimeAdapter._extract_reasoning(message) == "first pass\n\nsecond pass"
