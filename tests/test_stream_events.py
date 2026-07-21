"""Unit tests for stream event translation helpers."""

from __future__ import annotations

import json
from types import SimpleNamespace

from swarmmind.api.chat_routes import (
    ChatMessage,
    ChatRequest,
    _conversation_artifact_paths,
    _history_to_ui_messages,
    _native_human_message,
    _stream_chat,
    _strip_uploaded_files_tag,
)
from swarmmind.models import ConversationMode, ConversationRuntimeOptions
from swarmmind.services.stream_events import (
    deerflow_runtime_status_labels,
    serialize_stream_event,
    task_card_title,
    task_status_from_result,
    tool_activity_label,
    translate_deerflow_runtime_event,
)


def _opts(
    mode: ConversationMode, *, thinking: bool, subagent: bool, plan_mode: bool = False
) -> ConversationRuntimeOptions:
    return ConversationRuntimeOptions(
        mode=mode,
        model_name="test-model",
        thinking_enabled=thinking,
        plan_mode=plan_mode,
        subagent_enabled=subagent,
    )


def test_serialize_stream_event_outputs_ndjson_line():
    line = serialize_stream_event("assistant_message", message_id="m1", content="hello")
    assert line.endswith("\n")
    assert json.loads(line) == {"type": "assistant_message", "message_id": "m1", "content": "hello"}


def test_tool_activity_label_and_task_helpers_match_existing_behavior():
    assert tool_activity_label("search", {"query": "  abc  "}) == "检索资料：abc"
    assert tool_activity_label("search", {}) == "检索外部资料"
    assert tool_activity_label("unknown_tool") == "执行工具：unknown_tool"

    assert task_card_title({"description": "  收集信息  "}) == "收集信息"
    assert task_card_title({"prompt": "第一行\n第二行"}) == "第一行"
    assert task_card_title(None) == "新的协作分工"

    assert task_status_from_result("Task Succeeded. Result: done") == ("completed", "done")
    assert task_status_from_result("Task failed. reason") == ("failed", "reason")
    assert task_status_from_result("Task timed out after 60s") == ("failed", "Task timed out after 60s")
    assert task_status_from_result("keep running") == ("running", "keep running")


def test_deerflow_runtime_status_labels_by_mode():
    assert deerflow_runtime_status_labels(_opts(ConversationMode.ULTRA, thinking=True, subagent=True)) == (
        "正在判断这轮探索需要怎样的协作方式",
        "正在协作处理你的问题",
    )
    assert deerflow_runtime_status_labels(_opts(ConversationMode.PRO, thinking=True, subagent=False)) == (
        "正在规划这轮任务的执行方式",
        "正在按规划生成结果",
    )
    assert deerflow_runtime_status_labels(_opts(ConversationMode.THINKING, thinking=True, subagent=False)) == (
        "正在分析你的问题",
        "正在整理深入回复",
    )
    assert deerflow_runtime_status_labels(_opts(ConversationMode.FLASH, thinking=False, subagent=False)) == (
        "正在准备快速回复",
        "正在快速生成结果",
    )


def test_translate_reasoning_and_assistant_message_respects_runtime_flags():
    flash = _opts(ConversationMode.FLASH, thinking=False, subagent=False)
    thinking = _opts(ConversationMode.THINKING, thinking=True, subagent=False)

    assert (
        translate_deerflow_runtime_event(
            {"type": "assistant_reasoning", "message_id": "r1", "content": "thinking..."},
            flash,
        )
        == []
    )

    reasoning_lines = translate_deerflow_runtime_event(
        {"type": "assistant_reasoning", "message_id": "r1", "content": "thinking..."},
        thinking,
    )
    assert json.loads(reasoning_lines[0]) == {"type": "status.thinking", "mode": "thinking", "text": "thinking..."}

    assistant_lines = translate_deerflow_runtime_event(
        {"type": "assistant_message", "message_id": "a1", "content": "answer"},
        flash,
    )
    assert json.loads(assistant_lines[0]) == {"type": "content.accumulated", "text": "answer"}


def test_translate_tool_calls_and_tool_results_for_ultra_mode():
    ultra = _opts(ConversationMode.ULTRA, thinking=True, subagent=True, plan_mode=True)

    tool_call_lines = translate_deerflow_runtime_event(
        {
            "type": "assistant_tool_calls",
            "tool_calls": [
                {"name": "task", "args": {"description": "收集竞品资料"}, "id": "task-1"},
                {"name": "search", "args": {"query": "crm mvp"}, "id": "search-1"},
            ],
        },
        ultra,
    )
    # Task tool calls now produce task_started, team_activity, and status.running.
    assert len(tool_call_lines) == 3
    assert json.loads(tool_call_lines[0])["type"] == "task_started"
    assert json.loads(tool_call_lines[1])["type"] == "team_activity"
    task_line = json.loads(tool_call_lines[2])
    assert task_line["type"] == "status.running"
    assert task_line["step"] == 1
    assert task_line["text"] == "收集竞品资料"

    task_result = translate_deerflow_runtime_event(
        {
            "type": "tool_result",
            "tool_name": "task",
            "tool_call_id": "task-1",
            "content": "Task Succeeded. Result: 已完成",
        },
        ultra,
    )
    assert json.loads(task_result[0])["type"] == "task_completed"
    assert json.loads(task_result[1])["type"] == "team_activity"
    parsed_task_result = json.loads(task_result[2])
    assert parsed_task_result["type"] == "status.running"
    assert parsed_task_result["text"] == "已完成"

    # Search tool results no longer produce team_activity events in the auxiliary stream.
    activity_result = translate_deerflow_runtime_event(
        {
            "type": "tool_result",
            "tool_name": "search",
            "tool_call_id": "search-1",
            "content": "找到了 5 个相关来源",
        },
        ultra,
    )
    assert activity_result == []


def test_translate_clarification_and_custom_events():
    flash = _opts(ConversationMode.FLASH, thinking=False, subagent=False)
    ultra = _opts(ConversationMode.ULTRA, thinking=True, subagent=True, plan_mode=True)

    clarification_lines = translate_deerflow_runtime_event(
        {
            "type": "tool_result",
            "tool_name": "ask_clarification",
            "tool_call_id": "clarify-1",
            "content": "请提供目标用户信息",
        },
        flash,
    )
    assert json.loads(clarification_lines[0]) == {
        "type": "status.clarification",
        "question": "请提供目标用户信息",
    }

    started = translate_deerflow_runtime_event(
        {"type": "custom_event", "event_type": "task_started", "task_id": "t1", "description": "desc"},
        ultra,
    )
    running = translate_deerflow_runtime_event(
        {"type": "custom_event", "event_type": "task_running", "task_id": "t1", "message": "working"},
        ultra,
    )
    completed = translate_deerflow_runtime_event(
        {"type": "custom_event", "event_type": "task_completed", "task_id": "t1", "result": "ok"},
        ultra,
    )
    failed = translate_deerflow_runtime_event(
        {"type": "custom_event", "event_type": "task_failed", "task_id": "t1", "error": "boom"},
        ultra,
    )

    assert json.loads(started[0])["type"] == "task_started"
    assert json.loads(started[1])["type"] == "team_activity"
    assert json.loads(started[2])["type"] == "status.running"
    assert json.loads(running[0])["type"] == "task_running"
    assert json.loads(running[1])["type"] == "team_activity"
    assert json.loads(running[2])["type"] == "status.running"
    assert json.loads(completed[0])["type"] == "task_completed"
    assert json.loads(completed[1])["type"] == "team_activity"
    assert json.loads(completed[2])["type"] == "status.running"
    assert json.loads(failed[0])["type"] == "task_failed"
    assert json.loads(failed[1])["type"] == "team_activity"
    assert json.loads(failed[2])["type"] == "status.running"


def test_translate_plan_steps_event_from_values_mode():
    ultra = _opts(ConversationMode.ULTRA, thinking=True, subagent=True, plan_mode=True)
    flash = _opts(ConversationMode.FLASH, thinking=False, subagent=False)

    # plan_steps event is emitted regardless of subagent_enabled
    lines = translate_deerflow_runtime_event(
        {
            "type": "plan_steps",
            "steps": [
                {"description": "Step 1", "status": "completed"},
                {"description": "Step 2", "status": "pending"},
            ],
        },
        flash,
    )
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["type"] == "plan_steps"
    assert parsed["steps"] == [
        {"description": "Step 1", "status": "completed"},
        {"description": "Step 2", "status": "pending"},
    ]

    # Empty steps returns empty list
    empty = translate_deerflow_runtime_event({"type": "plan_steps", "steps": []}, ultra)
    assert empty == []

    # Missing steps returns empty list
    missing = translate_deerflow_runtime_event({"type": "plan_steps"}, ultra)
    assert missing == []


def test_chat_history_prefers_native_deerflow_payload():
    native = {
        "type": "ai",
        "id": "assistant-tool-call",
        "content": "",
        "additional_kwargs": {"reasoning_content": "先拆任务"},
        "response_metadata": {},
        "tool_calls": [
            {
                "name": "task",
                "args": {"description": "子任务"},
                "id": "call-task",
                "type": "tool_call",
            }
        ],
    }

    messages = _history_to_ui_messages(
        [
            SimpleNamespace(role="assistant", content="flattened fallback", native_payload=native),
            SimpleNamespace(role="assistant", content="plain answer", native_payload=None, id="plain"),
        ]
    )

    assert messages[0].type == "ai"
    assert messages[0].id == "assistant-tool-call"
    assert messages[0].content == ""
    assert messages[0].tool_calls == native["tool_calls"]
    assert messages[1].type == "ai"
    assert messages[1].content == "plain answer"


def test_chat_history_artifact_paths_keep_registered_deerflow_files_only():
    deps = SimpleNamespace(
        artifact_repo=SimpleNamespace(
            list_by_conversation=lambda _conversation_id: [
                SimpleNamespace(path="mnt/user-data/outputs/report.md", name=None),
                SimpleNamespace(path="/mnt/user-data/outputs/report.md", name=None),
                SimpleNamespace(path=None, name="/mnt/user-data/outputs/chart.svg"),
                SimpleNamespace(path="/tmp/internal.txt", name=None),
                SimpleNamespace(path=None, name="plain.md"),
            ]
        )
    )

    assert _conversation_artifact_paths(deps, "conv-1") == [
        "/mnt/user-data/outputs/report.md",
        "/mnt/user-data/outputs/chart.svg",
    ]


def test_chat_stream_injects_registered_artifacts_before_done():
    def stream_native_conversation_message(_conversation_id, _request):
        yield json.dumps(
            {
                "type": "deerflow.message",
                "message": {"type": "ai", "id": "a1", "content": "done", "additional_kwargs": {}, "response_metadata": {}},
            }
        )
        yield json.dumps({"type": "done"})

    deps = SimpleNamespace(
        conversation_repo=SimpleNamespace(),
        project_repo=SimpleNamespace(),
        artifact_repo=SimpleNamespace(
            list_by_conversation=lambda _conversation_id: [
                SimpleNamespace(path="/mnt/user-data/outputs/report.md", name=None),
            ]
        ),
        stream_native_conversation_message=stream_native_conversation_message,
        stream_native_project_message=None,
    )
    body = ChatRequest(
        conversation_id="conv-1",
        messages=[ChatMessage(type="human", content="write report")],
    )

    events = [json.loads(line) for line in _stream_chat(deps, body)]

    assert [event["type"] for event in events] == [
        "conversation_start",
        "deerflow.message",
        "artifacts",
        "done",
    ]
    assert events[2]["artifacts"] == ["/mnt/user-data/outputs/report.md"]


def test_chat_route_builds_native_human_message_with_upload_metadata():
    message = ChatMessage(
        type="human",
        content="Review this\n\n<uploaded_files>\n- brief.txt (12)\n  Path: /mnt/user-data/uploads/brief.txt\n</uploaded_files>",
        additional_kwargs={
            "files": [
                {
                    "filename": "brief.txt",
                    "size": 12,
                    "path": "/mnt/user-data/uploads/brief.txt",
                    "status": "uploaded",
                }
            ]
        },
    )

    native = _native_human_message(message, message.content)

    assert _strip_uploaded_files_tag(message.content) == "Review this"
    assert native["type"] == "human"
    assert native["content"] == message.content
    assert native["additional_kwargs"] == message.additional_kwargs
    assert native["response_metadata"] == {}


def test_translate_auxiliary_runtime_event_maps_required_types():
    """Verify required auxiliary UI event types are produced correctly."""
    ultra = _opts(ConversationMode.ULTRA, thinking=True, subagent=True, plan_mode=True)
    flash = _opts(ConversationMode.FLASH, thinking=False, subagent=False)

    events = []

    # status.thinking
    events.extend(translate_deerflow_runtime_event({"type": "assistant_reasoning", "content": "推理中..."}, ultra))
    # status.running (from tool call)
    events.extend(
        translate_deerflow_runtime_event(
            {"type": "assistant_tool_calls", "tool_calls": [{"name": "task", "args": {"description": "任务"}}]}, ultra
        )
    )
    # status.clarification
    events.extend(
        translate_deerflow_runtime_event(
            {"type": "tool_result", "tool_name": "ask_clarification", "content": "问题？"}, flash
        )
    )
    # status.artifact (from tool call)
    events.extend(
        translate_deerflow_runtime_event(
            {"type": "assistant_tool_calls", "tool_calls": [{"name": "present_files", "args": {}}]}, ultra
        )
    )
    # content.accumulated
    events.extend(translate_deerflow_runtime_event({"type": "assistant_message", "content": "正文"}, flash))

    parsed = [json.loads(e) for e in events]
    types = {e["type"] for e in parsed}
    assert "status.thinking" in types
    assert "status.running" in types
    assert "status.clarification" in types
    assert "status.artifact" in types
    assert "content.accumulated" in types


def test_flash_mode_suppresses_thinking_and_running_events():
    flash = _opts(ConversationMode.FLASH, thinking=False, subagent=False)

    reasoning = translate_deerflow_runtime_event({"type": "assistant_reasoning", "content": "思考..."}, flash)
    tool_calls = translate_deerflow_runtime_event(
        {"type": "assistant_tool_calls", "tool_calls": [{"name": "task", "args": {}}]}, flash
    )

    assert reasoning == []
    assert tool_calls == []
