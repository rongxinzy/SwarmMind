"""Tests for deterministic render helpers."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from swarmmind.models import MemoryContext
from swarmmind.renderer import (
    generate_conversation_title,
    generate_conversation_title_from_exchange,
    render_status,
)


def test_render_status_returns_empty_context_message(monkeypatch) -> None:
    class FakeMemory:
        def __init__(self, agent_id: str) -> None:
            assert agent_id == "status_renderer"

        def read_all(self, ctx=None):
            return []

    monkeypatch.setattr("swarmmind.renderer.LayeredMemory", FakeMemory)

    summary = render_status("  分析   本周   销售  ", ctx=MemoryContext(user_id="u-1", session_id="s-1"))

    assert summary == "当前还没有与“分析 本周 销售”相关的共享上下文。"


def test_render_status_uses_latest_five_entries_in_desc_order(monkeypatch) -> None:
    entries = [
        SimpleNamespace(key=f"k{i}", value=f"value {i}", created_at=datetime(2026, 1, i + 1, 0, 0, 0))
        for i in range(7, 0, -1)
    ]

    class FakeMemory:
        def __init__(self, agent_id: str) -> None:
            assert agent_id == "status_renderer"

        def read_all(self, ctx=None):
            return entries

    monkeypatch.setattr("swarmmind.renderer.LayeredMemory", FakeMemory)

    summary = render_status("季度复盘", ctx=MemoryContext(user_id="u-1", session_id="s-1"))

    assert "当前已沉淀 7 条共享上下文" in summary
    for key in ("k7", "k6", "k5", "k4", "k3"):
        assert key in summary
    for key in ("k2", "k1"):
        assert key not in summary


def test_generate_conversation_title_trims_and_truncates() -> None:
    title = generate_conversation_title(
        "   这是一个   很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长 的问题，需要被整理成标题，并且要继续补充更多背景信息   "
    )

    assert title.endswith("...")
    assert len(title) <= 50
    assert "  " not in title


def test_generate_conversation_title_from_exchange_is_deterministic_fallback() -> None:
    title, source = generate_conversation_title_from_exchange("  帮我总结今天的 standup  ", "好的")

    assert title == "帮我总结今天的 standup"
    assert source == "fallback"
