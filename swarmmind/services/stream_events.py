"""Stream event serialization and translation helpers.

This module extracts the stream-event translation logic from supervisor,
so it can be tested and reused independently.
"""

from __future__ import annotations

import json
import uuid

from swarmmind.models import ConversationMode, ConversationRuntimeOptions


def serialize_stream_event(event_type: str, **payload) -> str:
    """Serialize a single streaming event as NDJSON line."""
    return json.dumps({"type": event_type, **payload}, ensure_ascii=False) + "\n"


def tool_activity_label(tool_name: str, args: dict | None = None) -> str:
    """Build localized activity label for tool calls."""
    args = args or {}

    if tool_name == "search":
        query = args.get("query")
        if isinstance(query, str) and query.strip():
            return f"检索资料：{query.strip()[:60]}"
        return "检索外部资料"
    if tool_name == "crawl":
        return "抓取网页内容"
    if tool_name == "fetch":
        return "获取远端内容"
    if tool_name == "view_image":
        return "查看图像资料"
    if tool_name == "read_file":
        return "读取文件"
    if tool_name == "write_file":
        return "写入文件"
    if tool_name == "edit_file":
        return "编辑文件"
    if tool_name == "bash":
        return "执行命令"
    if tool_name == "present_files":
        return "整理输出产物"
    if tool_name == "ask_clarification":
        return "请求补充信息"
    if tool_name == "tool_search":
        return "搜索可用工具"

    return f"执行工具：{tool_name}"


def task_card_title(tool_args: dict | None) -> str:
    """Build a task card title from tool call args."""
    if not isinstance(tool_args, dict):
        return "新的协作分工"

    description = tool_args.get("description")
    if isinstance(description, str) and description.strip():
        return description.strip()

    prompt = tool_args.get("prompt")
    if isinstance(prompt, str) and prompt.strip():
        return prompt.strip().splitlines()[0][:80]

    return "新的协作分工"


def task_status_from_result(content: str) -> tuple[str, str | None]:
    """Derive task status/detail from task-tool result content."""
    normalized = content.strip()
    if normalized.startswith("Task Succeeded. Result:"):
        return "completed", normalized.split("Task Succeeded. Result:", 1)[1].strip() or None
    if normalized.startswith("Task failed."):
        return "failed", normalized.split("Task failed.", 1)[1].strip() or None
    if normalized.startswith("Task timed out"):
        return "failed", normalized
    return "running", normalized or None


def general_agent_status_labels(runtime_options: ConversationRuntimeOptions) -> tuple[str, str]:
    """Return phase labels for status events by runtime mode."""
    if runtime_options.mode == ConversationMode.ULTRA:
        return (
            "Agent Team 正在判断这轮探索需要怎样的协作方式",
            "Agent Team 正在协作处理你的问题",
        )
    if runtime_options.mode == ConversationMode.PRO:
        return (
            "正在规划这轮任务的执行方式",
            "正在按规划生成结果",
        )
    if runtime_options.mode == ConversationMode.THINKING:
        return (
            "正在分析你的问题",
            "正在整理深入回复",
        )
    return (
        "正在准备快速回复",
        "正在快速生成结果",
    )


def translate_general_agent_event(
    event: dict,
    runtime_options: ConversationRuntimeOptions,
) -> list[str]:
    """Translate DeerFlow/GeneralAgent events into supervisor stream events."""
    event_type = event.get("type")

    if event_type == "assistant_reasoning":
        if not runtime_options.thinking_enabled:
            return []
        content = event.get("content")
        if isinstance(content, str) and content.strip():
            return [
                serialize_stream_event(
                    "thinking",
                    message_id=event.get("message_id"),
                    content=content,
                ),
            ]
        return []

    if event_type == "assistant_message":
        content = event.get("content")
        if isinstance(content, str) and content:
            return [
                serialize_stream_event(
                    "assistant_message",
                    message_id=event.get("message_id"),
                    content=content,
                ),
            ]
        return []

    if event_type == "assistant_tool_calls":
        if not runtime_options.subagent_enabled:
            return []
        tool_calls = event.get("tool_calls")
        if not isinstance(tool_calls, list):
            return []

        lines: list[str] = []
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue

            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args", {})
            tool_call_id = tool_call.get("id")

            if tool_name == "task":
                lines.append(
                    serialize_stream_event(
                        "team_task",
                        task={
                            "id": tool_call_id,
                            "title": task_card_title(tool_args if isinstance(tool_args, dict) else {}),
                            "status": "running",
                            "detail": "Agent Team 正在协同处理这个子任务。",
                        },
                    ),
                )
                continue

            lines.append(
                serialize_stream_event(
                    "team_activity",
                    activity={
                        "id": tool_call_id or str(uuid.uuid4()),
                        "tool_name": tool_name,
                        "label": tool_activity_label(
                            str(tool_name),
                            tool_args if isinstance(tool_args, dict) else {},
                        ),
                        "status": "running",
                    },
                ),
            )
        return lines

    if event_type == "tool_result":
        tool_name = str(event.get("tool_name") or "unknown")
        tool_call_id = event.get("tool_call_id")
        content = str(event.get("content") or "").strip()

        # ask_clarification is available in all modes, not just subagent mode.
        if tool_name == "ask_clarification":
            return [
                serialize_stream_event(
                    "clarification_request",
                    clarification={
                        "id": tool_call_id,
                        "content": content,
                    },
                ),
            ]

        if not runtime_options.subagent_enabled:
            return []

        if tool_name == "task":
            status, detail = task_status_from_result(content)
            return [
                serialize_stream_event(
                    "team_task",
                    task={
                        "id": tool_call_id,
                        "status": status,
                        "detail": detail,
                    },
                ),
            ]

        return [
            serialize_stream_event(
                "team_activity",
                activity={
                    "id": tool_call_id or str(uuid.uuid4()),
                    "tool_name": tool_name,
                    "label": tool_activity_label(tool_name),
                    "status": "completed",
                    "detail": content[:240] if content else None,
                },
            ),
        ]

    if event_type == "custom_event":
        if not runtime_options.subagent_enabled:
            return []

        custom_event_type = event.get("event_type")
        task_id = event.get("task_id")

        if custom_event_type == "task_started":
            return [
                serialize_stream_event(
                    "task_started",
                    task={
                        "id": task_id,
                        "description": event.get("description"),
                        "status": "in_progress",
                    },
                ),
            ]

        if custom_event_type == "task_running":
            return [
                serialize_stream_event(
                    "task_running",
                    task={
                        "id": task_id,
                        "message": event.get("message"),
                    },
                ),
            ]

        if custom_event_type == "task_completed":
            return [
                serialize_stream_event(
                    "task_completed",
                    task={
                        "id": task_id,
                        "result": event.get("result"),
                        "status": "completed",
                    },
                ),
            ]

        if custom_event_type == "task_failed":
            return [
                serialize_stream_event(
                    "task_failed",
                    task={
                        "id": task_id,
                        "error": event.get("error"),
                        "status": "failed",
                    },
                ),
            ]

    return []


__all__ = [
    "general_agent_status_labels",
    "serialize_stream_event",
    "task_card_title",
    "task_status_from_result",
    "tool_activity_label",
    "translate_general_agent_event",
]
