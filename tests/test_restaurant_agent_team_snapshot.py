"""Regression test for ultra mode restaurant agent team snapshot.

Uses mock DeerFlow snapshot data to verify stream-event translation
and semantic-layer event sequences without requiring a live LLM.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from swarmmind.models import ConversationMode, ConversationRuntimeOptions
from swarmmind.services.stream_events import translate_general_agent_event

SNAPSHOTS_DIR = Path(__file__).with_suffix("").parent / "snapshots"
NDJSON_PATH = SNAPSHOTS_DIR / "ultra_restaurant_agent_team.ndjson"
META_PATH = SNAPSHOTS_DIR / "ultra_restaurant_agent_team.meta.json"

pytestmark = pytest.mark.skipif(
    not NDJSON_PATH.exists() or not META_PATH.exists(),
    reason="Snapshot files not present (internal harness artifacts)",
)

RUNTIME_OPTIONS = ConversationRuntimeOptions(
    mode=ConversationMode.ULTRA,
    model_name="test-model",
    thinking_enabled=True,
    plan_mode=True,
    subagent_enabled=True,
)


def _load_events() -> list[dict]:
    events = []
    with NDJSON_PATH.open("r", encoding="utf-8") as f:
        for raw_line in f:
            stripped = raw_line.strip()
            if stripped:
                events.append(json.loads(stripped))
    return events


def _load_meta() -> dict:
    with META_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


# -----------------------------------------------------------------------------
# Test 1: Snapshot integrity and structure
# -----------------------------------------------------------------------------
def test_snapshot_integrity_and_structure():
    meta = _load_meta()
    events = _load_events()

    # Event count matches meta
    assert len(events) == meta["event_count"]

    # Key event types exist
    types = {e["type"] for e in events}
    required_types = {
        "assistant_reasoning",
        "assistant_tool_calls",
        "tool_result",
        "assistant_message",
    }
    assert required_types <= types, f"Missing types: {required_types - types}"

    # Every event has 'type' and 'message_id' (custom_events may lack message_id)
    for i, event in enumerate(events):
        assert "type" in event, f"Event {i} missing 'type'"
        if event["type"] != "custom_event":
            assert "message_id" in event, f"Event {i} ({event['type']}) missing 'message_id'"


# -----------------------------------------------------------------------------
# Test 2: Semantic-layer event translation
# -----------------------------------------------------------------------------
def test_semantic_layer_event_translation():
    events = _load_events()
    semantic_events: list[dict] = []

    semantic_events.extend(
        json.loads(line) for event in events for line in translate_general_agent_event(event, RUNTIME_OPTIONS)
    )

    types = [e["type"] for e in semantic_events]

    # Sequence starts with status.thinking
    assert types[0] == "status.thinking", f"Expected status.thinking first, got {types[0]}"

    # Contains status.running (possibly multiple times)
    assert "status.running" in types, "Missing status.running in semantic events"

    # Contains at least one status.clarification
    assert "status.clarification" in types, "Missing status.clarification in semantic events"

    # Contains content.accumulated
    assert "content.accumulated" in types, "Missing content.accumulated in semantic events"

    # Sequence ends with content.accumulated (the last assistant_message)
    assert types[-1] == "content.accumulated", f"Expected content.accumulated last, got {types[-1]}"

    # No error events
    assert "error" not in types, f"Unexpected error events: {[e for e in semantic_events if e['type'] == 'error']}"


# -----------------------------------------------------------------------------
# Test 3: Business content validation
# -----------------------------------------------------------------------------
def test_business_content_validation():
    events = _load_events()
    semantic_events: list[dict] = []

    semantic_events.extend(
        json.loads(line) for event in events for line in translate_general_agent_event(event, RUNTIME_OPTIONS)
    )

    # Final assistant_message content should contain at least 2 of the keywords
    assistant_messages = [e for e in events if e["type"] == "assistant_message"]
    final_content = assistant_messages[-1]["content"]
    keywords = ["顾客", "厨师", "餐厅老板"]
    matched = [kw for kw in keywords if kw in final_content]
    assert len(matched) >= 2, f"Final content should contain at least 2 keywords from {keywords}, got {matched}"

    # Clarification event should contain "小费"
    clarification_events = [e for e in semantic_events if e["type"] == "status.clarification"]
    assert clarification_events, "No clarification events found"
    for clar in clarification_events:
        assert "小费" in clar.get("question", ""), f"Clarification missing '小费': {clar}"


# -----------------------------------------------------------------------------
# Test 4: Incremental streaming accumulation simulation
# -----------------------------------------------------------------------------
def test_incremental_streaming_accumulation():
    events = _load_events()
    assistant_messages = [e for e in events if e["type"] == "assistant_message"]

    # Simulate accumulation by concatenating all assistant_message contents in order
    accumulated = ""
    for msg in assistant_messages:
        accumulated += msg.get("content", "")

    assert accumulated, "Accumulated ai_response should not be empty"
    assert len(accumulated) > 50, f"Accumulated content too short ({len(accumulated)} chars)"
