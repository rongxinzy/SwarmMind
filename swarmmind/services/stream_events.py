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
    """Translate DeerFlow/GeneralAgent events into UI semantic layer stream events."""
    event_type = event.get("type")

    # 0. status.plan_steps
    if event_type == "plan_steps":
        steps = event.get("steps", [])
        if isinstance(steps, list) and steps:
            return [
                serialize_stream_event(
                    "status.plan_steps",
                    steps=[
                        {
                            "description": s.get("description", ""),
                            "status": s.get("status", "pending"),
                        }
                        for s in steps
                        if isinstance(s, dict)
                    ],
                ),
            ]
        return []

    # 1. status.thinking
    if event_type == "assistant_reasoning":
        if not runtime_options.thinking_enabled:
            return []
        content = event.get("content", "")
        if isinstance(content, str) and content.strip():
            return [
                serialize_stream_event(
                    "status.thinking",
                    mode=runtime_options.mode.value,
                    text=content,
                ),
            ]
        return []

    # 5. content.accumulated
    if event_type == "assistant_message":
        content = event.get("content", "")
        if isinstance(content, str) and content:
            return [serialize_stream_event("content.accumulated", text=content)]
        return []

    # 2. status.running & 4. status.artifact (from tool calls)
    if event_type == "assistant_tool_calls":
        if not runtime_options.subagent_enabled:
            return []
        tool_calls = event.get("tool_calls", [])
        if not isinstance(tool_calls, list):
            return []

        lines: list[str] = []
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args", {})
            tool_id = tool_call.get("id") or str(uuid.uuid4())

            if tool_name == "task":
                title = task_card_title(tool_args if isinstance(tool_args, dict) else {})
                lines.append(
                    serialize_stream_event(
                        "task_started",
                        task={
                            "id": tool_id,
                            "description": title,
                            "status": "in_progress",
                        },
                    ),
                )
                lines.append(
                    serialize_stream_event(
                        "team_activity",
                        activity={
                            "id": f"activity-{tool_id}",
                            "label": title,
                            "status": "running",
                            "detail": "子任务已启动",
                        },
                    ),
                )
                lines.append(
                    serialize_stream_event(
                        "status.running",
                        step=1,
                        total_steps=None,
                        text=title,
                    ),
                )
            elif tool_name in ("present_files", "write_file", "edit_file"):
                lines.append(
                    serialize_stream_event(
                        "status.artifact",
                        name=tool_activity_label(tool_name, tool_args if isinstance(tool_args, dict) else {}),
                        artifact_type=tool_name,
                    ),
                )
        return lines

    # 3. status.clarification, 2. status.running, 4. status.artifact (from tool results)
    if event_type == "tool_result":
        tool_name = str(event.get("tool_name") or "unknown")
        content = str(event.get("content") or "").strip()
        tool_call_id = event.get("tool_call_id") or str(uuid.uuid4())

        if tool_name == "ask_clarification":
            return [serialize_stream_event("status.clarification", question=content)]

        if not runtime_options.subagent_enabled:
            return []

        if tool_name == "task":
            task_status, detail = task_status_from_result(content)
            if task_status == "completed":
                lines = [
                    serialize_stream_event(
                        "task_completed",
                        task={
                            "id": tool_call_id,
                            "status": "completed",
                            "result": detail,
                        },
                    ),
                    serialize_stream_event(
                        "team_activity",
                        activity={
                            "id": f"activity-{tool_call_id}",
                            "label": "子任务完成",
                            "status": "completed",
                            "detail": detail or "子任务已成功完成",
                        },
                    ),
                ]
            else:
                lines = [
                    serialize_stream_event(
                        "task_failed",
                        task={
                            "id": tool_call_id,
                            "status": "failed",
                            "error": detail,
                        },
                    ),
                    serialize_stream_event(
                        "team_activity",
                        activity={
                            "id": f"activity-{tool_call_id}",
                            "label": "子任务失败",
                            "status": "completed",
                            "detail": detail or "子任务执行失败",
                        },
                    ),
                ]
            lines.append(
                serialize_stream_event(
                    "status.running",
                    step=1,
                    text=detail or "子任务更新",
                ),
            )
            return lines

        if tool_name in ("present_files", "write_file", "edit_file"):
            return [
                serialize_stream_event(
                    "status.artifact",
                    name=tool_activity_label(tool_name),
                    artifact_type=tool_name,
                ),
            ]

        return []

    # 2. status.running (from custom events)
    if event_type == "custom_event":
        if not runtime_options.subagent_enabled:
            return []

        custom_event_type = event.get("event_type")

        # Plan-mode step list visibility
        if custom_event_type == "plan_steps":
            steps = event.get("steps", [])
            if isinstance(steps, list) and steps:
                return [
                    serialize_stream_event(
                        "status.plan_steps",
                        steps=[
                            {
                                "description": s.get("description", ""),
                                "status": s.get("status", "pending"),
                            }
                            for s in steps
                            if isinstance(s, dict)
                        ],
                    ),
                ]
            return []

        if custom_event_type in ("task_started", "task_running", "task_completed", "task_failed"):
            task_id = event.get("task_id") or str(uuid.uuid4())
            text = (
                event.get("description")
                or event.get("message")
                or event.get("result")
                or event.get("error")
                or "子任务更新"
            )
            lines: list[str] = []

            if custom_event_type == "task_started":
                lines.append(
                    serialize_stream_event(
                        "task_started",
                        task={
                            "id": task_id,
                            "description": text,
                            "status": "in_progress",
                        },
                    ),
                )
                lines.append(
                    serialize_stream_event(
                        "team_activity",
                        activity={
                            "id": f"activity-{task_id}",
                            "label": text,
                            "status": "running",
                            "detail": "子任务已开始",
                        },
                    ),
                )
            elif custom_event_type == "task_running":
                lines.append(
                    serialize_stream_event(
                        "task_running",
                        task={
                            "id": task_id,
                            "message": event.get("message") or text,
                        },
                    ),
                )
                lines.append(
                    serialize_stream_event(
                        "team_activity",
                        activity={
                            "id": f"activity-{task_id}",
                            "label": text,
                            "status": "running",
                            "detail": "子任务执行中",
                        },
                    ),
                )
            elif custom_event_type == "task_completed":
                lines.append(
                    serialize_stream_event(
                        "task_completed",
                        task={
                            "id": task_id,
                            "status": "completed",
                            "result": event.get("result") or text,
                        },
                    ),
                )
                lines.append(
                    serialize_stream_event(
                        "team_activity",
                        activity={
                            "id": f"activity-{task_id}",
                            "label": "子任务完成",
                            "status": "completed",
                            "detail": text,
                        },
                    ),
                )
            elif custom_event_type == "task_failed":
                lines.append(
                    serialize_stream_event(
                        "task_failed",
                        task={
                            "id": task_id,
                            "status": "failed",
                            "error": event.get("error") or text,
                        },
                    ),
                )
                lines.append(
                    serialize_stream_event(
                        "team_activity",
                        activity={
                            "id": f"activity-{task_id}",
                            "label": "子任务失败",
                            "status": "completed",
                            "detail": text,
                        },
                    ),
                )

            lines.append(serialize_stream_event("status.running", step=1, text=text))
            return lines

    return []


__all__ = [
    "general_agent_status_labels",
    "serialize_stream_event",
    "task_card_title",
    "task_status_from_result",
    "tool_activity_label",
    "translate_general_agent_event",
]
