"""Regression tests for clarification middleware interception behavior."""

from __future__ import annotations

import logging
from unittest.mock import Mock

import pytest
from langchain_core.messages import ToolMessage
from langgraph.graph import END
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command

from swarmmind.agents.middlewares.clarification_middleware import ClarificationMiddleware


def _build_request(*, name: str, args: dict | None = None, tool_call_id: str = "tool-call-1") -> ToolCallRequest:
    return ToolCallRequest(
        tool_call={
            "id": tool_call_id,
            "name": name,
            "args": args or {},
            "type": "tool_call",
        },
        tool=None,
        state={},
        runtime=None,
    )


def test_wrap_tool_call_intercepts_ask_clarification(caplog: pytest.LogCaptureFixture) -> None:
    middleware = ClarificationMiddleware()
    request = _build_request(
        name="ask_clarification",
        args={
            "question": "请确认目标用户是谁？",
            "clarification_type": "missing_info",
            "context": "当前需求缺少核心用户画像。",
            "options": ["企业销售", "运营团队"],
        },
        tool_call_id="clarify-sync",
    )
    handler = Mock(side_effect=AssertionError("clarification requests should be intercepted"))

    with caplog.at_level(logging.INFO):
        result = middleware.wrap_tool_call(request, handler)

    assert isinstance(result, Command)
    assert result.goto == END
    assert len(result.update["messages"]) == 1
    message = result.update["messages"][0]
    assert isinstance(message, ToolMessage)
    assert message.tool_call_id == "clarify-sync"
    assert message.name == "ask_clarification"
    assert message.content == "❓ 当前需求缺少核心用户画像。\n\n请确认目标用户是谁？\n\n  1. 企业销售\n  2. 运营团队"
    handler.assert_not_called()
    assert "tool_call_id=clarify-sync" in caplog.text
    assert "clarification_type=missing_info" in caplog.text


@pytest.mark.asyncio
async def test_awrap_tool_call_intercepts_ask_clarification() -> None:
    middleware = ClarificationMiddleware()
    request = _build_request(
        name="ask_clarification",
        args={
            "question": "Which rollout should I use?",
            "clarification_type": "approach_choice",
            "options": ["Blue/green", "Canary"],
        },
        tool_call_id="clarify-async",
    )

    async def handler(_request: ToolCallRequest) -> ToolMessage:
        raise AssertionError("clarification requests should be intercepted")

    result = await middleware.awrap_tool_call(request, handler)

    assert isinstance(result, Command)
    assert result.goto == END
    assert len(result.update["messages"]) == 1
    message = result.update["messages"][0]
    assert isinstance(message, ToolMessage)
    assert message.tool_call_id == "clarify-async"
    assert message.name == "ask_clarification"
    assert message.content == "🔀 Which rollout should I use?\n\n  1. Blue/green\n  2. Canary"


def test_wrap_tool_call_passthrough_for_non_clarification_tools() -> None:
    middleware = ClarificationMiddleware()
    request = _build_request(name="search_docs", args={"query": "runtime profile"})
    expected = ToolMessage(content="ok", tool_call_id="tool-call-1", name="search_docs")
    handler = Mock(return_value=expected)

    result = middleware.wrap_tool_call(request, handler)

    assert result is expected
    handler.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_awrap_tool_call_passthrough_for_non_clarification_tools() -> None:
    middleware = ClarificationMiddleware()
    request = _build_request(name="search_docs", args={"query": "runtime profile"})
    expected = ToolMessage(content="ok", tool_call_id="tool-call-1", name="search_docs")

    async def handler(_request: ToolCallRequest) -> ToolMessage:
        assert _request is request
        return expected

    result = await middleware.awrap_tool_call(request, handler)

    assert result is expected
