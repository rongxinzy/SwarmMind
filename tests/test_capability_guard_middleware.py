"""Tests for CapabilityGuardMiddleware."""

import json
from unittest.mock import MagicMock, AsyncMock

import pytest

from swarmmind.agents.middlewares.capability_guard_middleware import (
    CapabilityGuardMiddleware,
    GUARD_MARKER,
)
from swarmmind.services.risk_policy import RiskTier
from swarmmind.services.run_context import RiskPolicy


def _make_request(tool_name: str, args: dict | None = None, tool_call_id: str = "tc-1"):
    req = MagicMock()
    req.tool_call = {"name": tool_name, "args": args or {}, "id": tool_call_id}
    return req


class TestCapabilityGuardMiddleware:
    def test_permissive_policy_never_blocks(self):
        mw = CapabilityGuardMiddleware(risk_policy=RiskPolicy.PERMISSIVE)
        handler = MagicMock(return_value="executed")
        req = _make_request("shell")
        result = mw.wrap_tool_call(req, handler)
        handler.assert_called_once_with(req)
        assert result == "executed"

    def test_moderate_policy_blocks_high_risk(self):
        mw = CapabilityGuardMiddleware(risk_policy=RiskPolicy.MODERATE)
        handler = MagicMock()
        req = _make_request("shell")
        result = mw.wrap_tool_call(req, handler)
        handler.assert_not_called()
        # Result should be a Command
        assert hasattr(result, "update") or hasattr(result, "goto")

    def test_moderate_policy_allows_medium_risk(self):
        mw = CapabilityGuardMiddleware(risk_policy=RiskPolicy.MODERATE)
        handler = MagicMock(return_value="ok")
        req = _make_request("write_file")  # medium risk
        result = mw.wrap_tool_call(req, handler)
        handler.assert_called_once()
        assert result == "ok"

    def test_strict_policy_blocks_medium_risk(self):
        mw = CapabilityGuardMiddleware(risk_policy=RiskPolicy.STRICT)
        handler = MagicMock()
        req = _make_request("write_file")  # medium risk
        result = mw.wrap_tool_call(req, handler)
        handler.assert_not_called()
        assert hasattr(result, "update") or hasattr(result, "goto")

    def test_guard_embeds_marker_in_tool_message(self):
        mw = CapabilityGuardMiddleware(risk_policy=RiskPolicy.MODERATE)
        req = _make_request("shell", args={"cmd": "rm -rf /"})
        result = mw.wrap_tool_call(req, MagicMock())
        # The Command's update should contain a ToolMessage with the marker
        messages = result.update.get("messages", [])
        assert messages, "Expected messages in Command update"
        content = messages[0].content
        parsed = json.loads(content)
        assert parsed[GUARD_MARKER] is True
        assert parsed["capability"] == "shell"
        assert parsed["risk_tier"] == RiskTier.HIGH.value

    def test_on_guard_callback_fires(self):
        captured = []

        def cb(cap, tier, evidence):
            captured.append((cap, tier, evidence))

        mw = CapabilityGuardMiddleware(risk_policy=RiskPolicy.MODERATE, on_guard=cb)
        mw.wrap_tool_call(_make_request("shell"), MagicMock())
        assert len(captured) == 1
        assert captured[0][0] == "shell"
        assert captured[0][1] == RiskTier.HIGH.value

    def test_on_guard_callback_not_called_for_safe_tool(self):
        captured = []
        mw = CapabilityGuardMiddleware(
            risk_policy=RiskPolicy.MODERATE, on_guard=lambda *a: captured.append(a)
        )
        handler = MagicMock(return_value="ok")
        mw.wrap_tool_call(_make_request("web_search"), handler)
        assert captured == []
        handler.assert_called_once()

    def test_on_guard_callback_exception_is_swallowed(self):
        def bad_cb(*args):
            raise RuntimeError("boom")

        mw = CapabilityGuardMiddleware(risk_policy=RiskPolicy.MODERATE, on_guard=bad_cb)
        # Should not raise
        result = mw.wrap_tool_call(_make_request("shell"), MagicMock())
        assert result is not None

    @pytest.mark.asyncio
    async def test_awrap_tool_call_blocks_high_risk(self):
        mw = CapabilityGuardMiddleware(risk_policy=RiskPolicy.MODERATE)
        async_handler = AsyncMock()
        req = _make_request("shell")
        result = await mw.awrap_tool_call(req, async_handler)
        async_handler.assert_not_called()
        assert hasattr(result, "update") or hasattr(result, "goto")

    @pytest.mark.asyncio
    async def test_awrap_tool_call_passes_safe_tool(self):
        mw = CapabilityGuardMiddleware(risk_policy=RiskPolicy.MODERATE)
        async_handler = AsyncMock(return_value="ok")
        req = _make_request("search")
        result = await mw.awrap_tool_call(req, async_handler)
        async_handler.assert_called_once()
        assert result == "ok"
