"""Tests for TraceService — collaboration trace reconstruction."""

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from swarmmind.services.trace_service import LEGACY_DEFAULT_CHECKPOINTER_PATH, TraceService


@pytest.fixture
def temp_checkpointer_db():
    """Create a temporary checkpointer database with sample checkpoints."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create checkpoints table (matches langgraph SqliteSaver schema)
    cursor.execute("""
        CREATE TABLE checkpoints (
            thread_id TEXT NOT NULL,
            checkpoint_ns TEXT NOT NULL DEFAULT '',
            checkpoint_id TEXT NOT NULL,
            parent_checkpoint_id TEXT,
            type TEXT,
            checkpoint BLOB,
            metadata BLOB,
            PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
        )
    """)

    # Insert sample checkpoints
    thread_id = "test-thread-001"

    # Checkpoint 1: Initial state with user message
    cp1 = {
        "messages": [{"type": "human", "content": "帮我分析 Q3 财报"}],
        "artifacts": [],
        "todos": [],
    }
    cursor.execute(
        """
        INSERT INTO checkpoints
        (thread_id, checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            thread_id,
            "cp-001",
            None,
            "checkpoint",
            json.dumps(cp1),
            json.dumps({"created_at": "2026-01-01T10:00:00Z"}),
        ),
    )

    # Checkpoint 2: AI thinking + tool call
    cp2 = {
        "messages": [
            {"type": "human", "content": "帮我分析 Q3 财报"},
            {
                "type": "ai",
                "content": "我来帮您分析 Q3 财报...",
                "tool_calls": [{"id": "tc-001", "name": "web_search", "args": {"query": "Q3 财报分析"}}],
            },
        ],
        "artifacts": [],
        "todos": [{"id": 1, "content": "搜索 Q3 数据", "done": True}],
    }
    cursor.execute(
        """
        INSERT INTO checkpoints
        (thread_id, checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            thread_id,
            "cp-002",
            "cp-001",
            "checkpoint",
            json.dumps(cp2),
            json.dumps({"created_at": "2026-01-01T10:00:05Z"}),
        ),
    )

    # Checkpoint 3: Tool result + final response
    cp3 = {
        "messages": [
            {"type": "human", "content": "帮我分析 Q3 财报"},
            {
                "type": "ai",
                "content": "我来帮您分析 Q3 财报...",
                "tool_calls": [{"id": "tc-001", "name": "web_search", "args": {"query": "Q3 财报分析"}}],
            },
            {
                "type": "tool",
                "name": "web_search",
                "content": "Q3 营收增长 15%...",
                "tool_call_id": "tc-001",
            },
            {"type": "ai", "content": "根据搜索结果，Q3 营收增长 15%..."},
        ],
        "artifacts": ["/mnt/user-data/outputs/q3_report.md"],
        "todos": [{"id": 1, "content": "搜索 Q3 数据", "done": True}],
    }
    cursor.execute(
        """
        INSERT INTO checkpoints
        (thread_id, checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            thread_id,
            "cp-003",
            "cp-002",
            "checkpoint",
            json.dumps(cp3),
            json.dumps({"created_at": "2026-01-01T10:00:10Z"}),
        ),
    )

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


class TestTraceService:
    """Test TraceService collaboration trace reconstruction."""

    def test_service_initialization_uses_legacy_default_without_runtime_env(self, monkeypatch):
        """Test TraceService keeps the legacy repo-local fallback without runtime env."""
        monkeypatch.delenv("DEER_FLOW_HOME", raising=False)
        service = TraceService()

        assert service.checkpointer_path == LEGACY_DEFAULT_CHECKPOINTER_PATH

    def test_service_initialization_uses_runtime_home_parent_checkpoint_path(self, monkeypatch, tmp_path):
        """Test TraceService follows SwarmMind runtime bundle layout under DEER_FLOW_HOME/home."""
        runtime_root = tmp_path / "runtime-instance"
        runtime_home = runtime_root / "home"
        runtime_home.mkdir(parents=True)
        monkeypatch.setenv("DEER_FLOW_HOME", str(runtime_home))

        service = TraceService()

        assert service.checkpointer_path == runtime_root / "checkpoints.db"

    def test_service_initialization_prefers_existing_runtime_home_checkpoint(self, monkeypatch, tmp_path):
        """Test TraceService uses an existing checkpoints.db inside DEER_FLOW_HOME."""
        runtime_home = tmp_path / "custom-home"
        runtime_home.mkdir(parents=True)
        expected_path = runtime_home / "checkpoints.db"
        expected_path.touch()
        monkeypatch.setenv("DEER_FLOW_HOME", str(runtime_home))

        service = TraceService()

        assert service.checkpointer_path == expected_path

    def test_service_initialization_with_custom_path(self):
        """Test TraceService can be initialized with custom path."""
        custom_path = "/tmp/custom.db"
        service = TraceService(custom_path)
        assert str(service.checkpointer_path) == custom_path

    def test_get_trace_returns_empty_for_missing_db(self):
        """Test get_conversation_trace returns empty trace when DB doesn't exist."""
        service = TraceService("/nonexistent/path.db")
        trace = service.get_conversation_trace("any-thread")

        assert trace["status"] == "empty"
        assert trace["events"] == []
        assert trace["checkpoint_count"] == 0

    def test_get_trace_returns_empty_when_checkpoints_table_is_missing(self, tmp_path):
        """Test get_conversation_trace degrades gracefully if upstream schema is absent."""
        db_path = tmp_path / "missing-table.db"
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE unrelated (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        service = TraceService(str(db_path))
        trace = service.get_conversation_trace("any-thread")

        assert trace["status"] == "empty"
        assert trace["events"] == []
        assert trace["checkpoint_count"] == 0

    def test_get_trace_reconstructs_events(self, temp_checkpointer_db):
        """Test get_conversation_trace correctly reconstructs events from checkpoints."""
        service = TraceService(temp_checkpointer_db)
        trace = service.get_conversation_trace("test-thread-001")

        # Verify structure
        assert trace["thread_id"] == "test-thread-001"
        assert trace["checkpoint_count"] == 3
        assert len(trace["events"]) > 0

        # Verify event types
        event_types = [e["type"] for e in trace["events"]]
        assert "user_input" in event_types
        assert "subagent_dispatch" in event_types  # AI with tool_calls
        assert "tool_execution" in event_types
        assert "assistant_response" in event_types
        assert "artifact_created" in event_types

        # Verify status
        assert trace["status"] in ("completed", "running")

        # Verify summary
        assert "用户输入" in trace["summary"]

    def test_convert_message_to_event_user_input(self):
        """Test _convert_message_to_event handles human messages."""
        service = TraceService()
        msg = {"type": "human", "content": "Hello"}

        event = service._convert_message_to_event(msg, 0, {})

        assert event is not None
        assert event["type"] == "user_input"
        assert event["agent_id"] == "user"
        assert event["content"] == "Hello"

    def test_convert_message_to_event_ai_response(self):
        """Test _convert_message_to_event handles AI messages."""
        service = TraceService()
        msg = {"type": "ai", "content": "Here's the answer..."}

        event = service._convert_message_to_event(msg, 1, {})

        assert event is not None
        assert event["type"] == "assistant_response"
        assert event["agent_id"] == "lead_agent"
        assert "answer" in event["content"]

    def test_convert_message_to_event_ai_with_tool_calls(self):
        """Test _convert_message_to_event handles AI messages with tool calls."""
        service = TraceService()
        msg = {
            "type": "ai",
            "content": "",
            "tool_calls": [{"id": "tc-1", "name": "web_search", "args": {"query": "test"}}],
        }

        event = service._convert_message_to_event(msg, 2, {})

        assert event is not None
        assert event["type"] == "subagent_dispatch"
        assert "tool_calls" in event
        assert len(event["tool_calls"]) == 1

    def test_convert_message_to_event_tool_result(self):
        """Test _convert_message_to_event handles tool messages."""
        service = TraceService()
        msg = {"type": "tool", "name": "bash", "content": "output here", "tool_call_id": "tc-1"}

        event = service._convert_message_to_event(msg, 3, {})

        assert event is not None
        assert event["type"] == "tool_execution"
        assert event["agent_id"] == "bash"
        assert event["result"] == "output here"

    def test_truncate_content(self):
        """Test _truncate_content limits string length."""
        service = TraceService()
        long_text = "a" * 2000

        truncated = service._truncate_content(long_text, 100)

        assert len(truncated) <= 103  # 100 + "..."
        assert truncated.endswith("...")

    def test_extract_reasoning_from_tags(self):
        """Test _extract_reasoning extracts content from <thinking> tags."""
        service = TraceService()
        content = "Some text <thinking>reasoning here</thinking> more text"

        reasoning = service._extract_reasoning(content)

        assert reasoning == "reasoning here"

    def test_extract_reasoning_from_blocks(self):
        """Test _extract_reasoning extracts content from content blocks."""
        service = TraceService()
        content = [{"type": "thinking", "thinking": "block reasoning"}]

        reasoning = service._extract_reasoning(content)

        assert reasoning == "block reasoning"
