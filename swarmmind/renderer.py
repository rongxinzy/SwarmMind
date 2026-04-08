"""Deterministic render helpers for conversation metadata."""

from __future__ import annotations

import re

from swarmmind.layered_memory import LayeredMemory
from swarmmind.models import MemoryContext


def _collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _trim_title(value: str, *, limit: int = 60) -> str:
    cleaned = _collapse_whitespace(value).strip(" ,.;:!?-")
    if not cleaned:
        return "New Conversation"
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def render_status(goal: str, ctx: MemoryContext | None = None, reasoning: bool = False) -> str:
    """Render a deterministic status summary from layered memory."""
    del reasoning

    memory = LayeredMemory(agent_id="status_renderer")
    entries = memory.read_all(ctx=ctx)
    if not entries:
        return f"当前还没有与“{_collapse_whitespace(goal)}”相关的共享上下文。"

    latest_entries = entries[-5:]
    fragments = [
        f"{entry.key}: {_collapse_whitespace(entry.value)[:120]}" for entry in latest_entries
    ]
    return (
        f"围绕“{_collapse_whitespace(goal)}”当前已沉淀 {len(entries)} 条共享上下文。"
        f"最近的关键信息包括：{'；'.join(fragments)}。"
    )


def generate_conversation_title(user_message: str) -> str:
    """Generate a short deterministic title from the first user message."""
    return _trim_title(user_message, limit=50)


def generate_conversation_title_from_exchange(
    user_message: str,
    assistant_message: str,
) -> tuple[str, str]:
    """Generate a deterministic title from the first complete exchange."""
    del assistant_message
    return generate_conversation_title(user_message), "fallback"
