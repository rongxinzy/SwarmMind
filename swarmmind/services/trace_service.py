"""协作轨迹服务 — 从 deer-flow checkpointer 读取并转换。

设计原则：
1. 零侵入 deer-flow — 只读取其持久化的 checkpoints
2. 复用 langgraph SqliteSaver 的表结构
3. 从 ThreadState 重建协作轨迹
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# 复用 deer-flow 的 runtime root 路径结构
DEFAULT_CHECKPOINTER_PATH = (
    Path(__file__).resolve().parents[2] / ".runtime" / "deerflow" / "local-default" / "checkpoints.db"
)


class TraceService:
    """从 deer-flow checkpointer 解析协作轨迹。

    直接读取 langgraph SqliteSaver 的数据库，解析 ThreadState，
    转换为 SwarmMind 的协作轨迹格式。
    """

    def __init__(self, checkpointer_path: Path | str | None = None) -> None:
        """Initialize trace service.

        Args:
            checkpointer_path: Path to SqliteSaver database.
                Defaults to deer-flow's default location.
        """
        self.checkpointer_path = Path(checkpointer_path) if checkpointer_path else DEFAULT_CHECKPOINTER_PATH

    def get_conversation_trace(self, thread_id: str) -> dict[str, Any]:
        """获取会话的协作轨迹。

        从 checkpointer 读取 checkpoints，解析 ThreadState，
        构建协作轨迹事件列表。

        Args:
            thread_id: The conversation thread ID (same as deer-flow thread_id).

        Returns:
            Dict with thread_id, status, events, summary.
        """
        if not self.checkpointer_path.exists():
            logger.warning("Checkpointer database not found at %s", self.checkpointer_path)
            return self._empty_trace(thread_id)

        checkpoints = self._load_checkpoints(thread_id)
        if not checkpoints:
            logger.debug("No checkpoints found for thread %s", thread_id)
            return self._empty_trace(thread_id)

        # 构建轨迹事件
        events = self._build_trace_events(checkpoints)

        return {
            "thread_id": thread_id,
            "status": self._determine_status(events),
            "events": events,
            "summary": self._generate_summary(events),
            "checkpoint_count": len(checkpoints),
        }

    def _load_checkpoints(self, thread_id: str) -> list[dict[str, Any]]:
        """Load checkpoints from SqliteSaver database.

        复用 deer-flow/langgraph 的 checkpoints 表结构:
        - thread_id TEXT
        - checkpoint_ns TEXT
        - checkpoint_id TEXT
        - parent_checkpoint_id TEXT
        - type TEXT
        - checkpoint BLOB (JSON serialized ThreadState)
        - metadata BLOB
        """
        conn = sqlite3.connect(self.checkpointer_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row

        try:
            cursor = conn.cursor()
            # 复用 SqliteSaver 的查询模式
            cursor.execute(
                """
                SELECT thread_id, checkpoint_id, parent_checkpoint_id, type, 
                       checkpoint, metadata
                FROM checkpoints 
                WHERE thread_id = ? AND checkpoint_ns = ''
                ORDER BY checkpoint_id ASC
                """,
                (thread_id,),
            )

            checkpoints = []
            for row in cursor.fetchall():
                try:
                    checkpoint_data = json.loads(row["checkpoint"]) if row["checkpoint"] else {}
                    metadata = json.loads(row["metadata"]) if row["metadata"] else {}
                except json.JSONDecodeError as e:
                    logger.warning("Failed to parse checkpoint %s: %s", row["checkpoint_id"], e)
                    continue

                checkpoints.append(
                    {
                        "thread_id": row["thread_id"],
                        "checkpoint_id": row["checkpoint_id"],
                        "parent_checkpoint_id": row["parent_checkpoint_id"],
                        "type": row["type"],
                        "checkpoint": checkpoint_data,
                        "metadata": metadata,
                    }
                )

            return checkpoints
        finally:
            conn.close()

    def _build_trace_events(self, checkpoints: list[dict]) -> list[dict[str, Any]]:
        """Build trace events from checkpoints.

        从 ThreadState 提取关键事件:
        - messages: 对话历史 (human/ai/tool)
        - artifacts: 产物创建
        - todos: 计划模式任务
        """
        events = []
        event_id = 0

        # 使用第一个和最后一个 checkpoint 来 diff 变化
        prev_state: dict[str, Any] = {}

        for cp in checkpoints:
            state = cp.get("checkpoint", {})
            metadata = cp.get("metadata", {})

            # 提取 messages
            messages = state.get("messages", [])
            prev_messages = prev_state.get("messages", [])

            # 找出新消息
            new_messages = messages[len(prev_messages) :]
            for msg in new_messages:
                event = self._convert_message_to_event(msg, event_id, metadata)
                if event:
                    events.append(event)
                    event_id += 1

            # 提取 artifacts 创建事件
            artifacts = state.get("artifacts", [])
            prev_artifacts = prev_state.get("artifacts", [])
            new_artifacts = [a for a in artifacts if a not in prev_artifacts]

            for artifact in new_artifacts:
                events.append(
                    {
                        "id": event_id,
                        "type": "artifact_created",
                        "agent_id": "system",
                        "agent_status": "acting",
                        "content": f"创建产物: {artifact}",
                        "artifact_path": artifact,
                        "timestamp": metadata.get("created_at") or datetime.now(UTC).isoformat(),
                    }
                )
                event_id += 1

            # 提取 todos 变化 (plan_mode)
            todos = state.get("todos", [])
            prev_todos = prev_state.get("todos", [])
            if len(todos) != len(prev_todos):
                # 简化处理：只记录 todo 列表变化
                events.append(
                    {
                        "id": event_id,
                        "type": "todos_updated",
                        "agent_id": "lead_agent",
                        "agent_status": "planning",
                        "content": f"更新任务计划: {len(todos)} 个待办",
                        "todos_count": len(todos),
                        "timestamp": metadata.get("created_at") or datetime.now(UTC).isoformat(),
                    }
                )
                event_id += 1

            prev_state = state

        return events

    def _convert_message_to_event(
        self, msg: dict[str, Any], event_id: int, metadata: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Convert LangChain message to trace event.

        复用 deer-flow 的消息类型:
        - human: 用户输入
        - ai: 助手回复 (可能包含 tool_calls)
        - tool: 工具执行结果
        """
        msg_type = msg.get("type", "unknown")
        content = msg.get("content", "")
        timestamp = metadata.get("created_at") or datetime.now(UTC).isoformat()

        # 截断长内容
        content_preview = self._truncate_content(content, 1000)

        if msg_type == "human":
            return {
                "id": event_id,
                "type": "user_input",
                "agent_id": "user",
                "agent_status": "input",
                "content": self._truncate_content(content, 500),
                "timestamp": timestamp,
            }

        if msg_type == "ai":
            tool_calls = msg.get("tool_calls", [])

            if tool_calls:
                # 子代理委派事件
                return {
                    "id": event_id,
                    "type": "subagent_dispatch",
                    "agent_id": "lead_agent",
                    "agent_status": "acting",
                    "content": f"调用工具: {tool_calls[0].get('name', 'unknown')}",
                    "tool_calls": [
                        {
                            "id": tc.get("id"),
                            "name": tc.get("name"),
                            "args": self._truncate_content(json.dumps(tc.get("args", {})), 200),
                        }
                        for tc in tool_calls
                    ],
                    "timestamp": timestamp,
                }
            # 普通 AI 回复
            reasoning = self._extract_reasoning(content)
            return {
                "id": event_id,
                "type": "assistant_response",
                "agent_id": "lead_agent",
                "agent_status": "thinking" if reasoning else "acting",
                "content": content_preview,
                "reasoning": reasoning,
                "timestamp": timestamp,
            }

        if msg_type == "tool":
            return {
                "id": event_id,
                "type": "tool_execution",
                "agent_id": msg.get("name", "tool"),
                "agent_status": "acting",
                "content": f"工具: {msg.get('name', 'unknown')}",
                "result": content_preview,
                "tool_call_id": msg.get("tool_call_id"),
                "timestamp": timestamp,
            }

        return None

    def _extract_reasoning(self, content: str | list) -> str | None:
        """Extract reasoning/thinking content from message.

        复用 deer-flow 的模式：某些模型会在 content 中返回 reasoning。
        """
        if isinstance(content, list):
            # 处理 content block 格式
            for block in content:
                if isinstance(block, dict) and block.get("type") == "thinking":
                    return block.get("thinking", "")
        elif isinstance(content, str):
            # 简单启发式：查找常见的 reasoning 标记
            if "<thinking>" in content and "</thinking>" in content:
                start = content.find("<thinking>") + len("<thinking>")
                end = content.find("</thinking>")
                if end > start:
                    return content[start:end].strip()
        return None

    def _truncate_content(self, content: Any, max_length: int = 1000) -> str:
        """Truncate content to max length."""
        text = str(content) if content else ""
        if len(text) > max_length:
            return text[: max_length - 3] + "..."
        return text

    def _determine_status(self, events: list[dict]) -> str:
        """Determine overall status from events."""
        if not events:
            return "empty"

        last_event = events[-1]
        event_type = last_event.get("type")

        if event_type == "user_input":
            return "waiting"
        if event_type in ("assistant_response", "artifact_created"):
            return "completed"
        if event_type == "tool_execution":
            return "running"
        if event_type == "subagent_dispatch":
            return "delegating"

        return "unknown"

    def _generate_summary(self, events: list[dict]) -> str:
        """Generate human-readable summary."""
        if not events:
            return "暂无执行记录"

        stats = {
            "user_inputs": len([e for e in events if e["type"] == "user_input"]),
            "assistant_responses": len([e for e in events if e["type"] == "assistant_response"]),
            "tool_calls": len([e for e in events if e["type"] == "tool_execution"]),
            "subagent_dispatches": len([e for e in events if e["type"] == "subagent_dispatch"]),
            "artifacts": len([e for e in events if e["type"] == "artifact_created"]),
        }

        parts = []
        if stats["user_inputs"]:
            parts.append(f"用户输入 {stats['user_inputs']} 轮")
        if stats["subagent_dispatches"]:
            parts.append(f"子代理协作 {stats['subagent_dispatches']} 次")
        if stats["tool_calls"]:
            parts.append(f"工具调用 {stats['tool_calls']} 次")
        if stats["artifacts"]:
            parts.append(f"生成产物 {stats['artifacts']} 个")

        return "，".join(parts) if parts else "执行完成"

    def _empty_trace(self, thread_id: str) -> dict[str, Any]:
        """Return empty trace structure."""
        return {
            "thread_id": thread_id,
            "status": "empty",
            "events": [],
            "summary": "暂无执行记录",
            "checkpoint_count": 0,
        }


# 全局服务实例（复用 deer-flow 的单例模式）
trace_service = TraceService()
