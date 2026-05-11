"""Middleware that intercepts tool calls and blocks medium/high-risk capabilities.

When a tool call is classified as medium or high risk (according to the run's
RiskPolicy), this middleware:
1. Calls the on_guard callback with capability metadata.
2. Returns a Command that interrupts execution (goto=END) with a marker
   ToolMessage so the execution service can create an ApprovalRequest.

The tool is NOT executed — the run pauses pending an approval decision.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import override

from langchain_core.messages import ToolMessage
from langgraph.graph import END
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command

try:
    from langchain.agents import AgentState
    from langchain.agents.middleware import AgentMiddleware
except ImportError:  # pragma: no cover — guarded import for test isolation
    AgentState = object  # type: ignore[assignment,misc]
    AgentMiddleware = object  # type: ignore[assignment,misc]

from swarmmind.services.risk_policy import RiskTier, classify
from swarmmind.services.run_context import RiskPolicy

logger = logging.getLogger(__name__)

# Marker key embedded in the ToolMessage content so the execution service can
# detect capability-guard events without needing a separate event channel.
GUARD_MARKER = "__capability_guard__"


class CapabilityGuardMiddleware(AgentMiddleware):
    """Blocks tool calls that exceed the run's configured risk threshold."""

    state_schema = AgentState if AgentState is not object else None  # type: ignore[assignment]

    def __init__(
        self,
        risk_policy: RiskPolicy,
        on_guard: Callable[[str, str, dict], None] | None = None,
    ) -> None:
        """Args:
        risk_policy: Determines which tiers trigger the guard.
            MODERATE → block HIGH only.
            STRICT   → block MEDIUM and HIGH.
            PERMISSIVE → block nothing (middleware is a no-op).
        on_guard: Optional callback invoked (synchronously) when a guard
            fires. Signature: on_guard(capability, risk_tier_value, evidence).
        """
        self._risk_policy = risk_policy
        self._on_guard = on_guard

    def _should_block(self, tier: RiskTier) -> bool:
        if self._risk_policy == RiskPolicy.PERMISSIVE:
            return False
        if self._risk_policy == RiskPolicy.STRICT:
            return tier in (RiskTier.MEDIUM, RiskTier.HIGH)
        # MODERATE: only HIGH
        return tier == RiskTier.HIGH

    def _build_guard_command(
        self,
        tool_call_id: str,
        tool_name: str,
        tier: RiskTier,
        args: dict,
    ) -> Command:
        evidence = {"tool_name": tool_name, "args": args}
        content = json.dumps(
            {
                GUARD_MARKER: True,
                "capability": tool_name,
                "risk_tier": tier.value,
                "evidence": evidence,
            },
            ensure_ascii=False,
        )
        tool_message = ToolMessage(
            content=content,
            tool_call_id=tool_call_id,
            name=tool_name,
        )
        logger.info(
            "Capability guard triggered: tool=%s tier=%s policy=%s",
            tool_name,
            tier.value,
            self._risk_policy.value,
        )
        if self._on_guard is not None:
            try:
                self._on_guard(tool_name, tier.value, evidence)
            except Exception:
                logger.exception("on_guard callback raised an exception")
        return Command(update={"messages": [tool_message]}, goto=END)

    @override
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        tool_name: str = request.tool_call.get("name", "")
        tier = classify(tool_name)
        if not self._should_block(tier):
            return handler(request)
        args: dict = request.tool_call.get("args", {})
        tool_call_id: str = request.tool_call.get("id", "")
        return self._build_guard_command(tool_call_id, tool_name, tier, args)

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        tool_name: str = request.tool_call.get("name", "")
        tier = classify(tool_name)
        if not self._should_block(tier):
            return await handler(request)
        args: dict = request.tool_call.get("args", {})
        tool_call_id: str = request.tool_call.get("id", "")
        return self._build_guard_command(tool_call_id, tool_name, tier, args)
