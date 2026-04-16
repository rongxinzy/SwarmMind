"""Unit tests for stream event translation helpers."""

from __future__ import annotations

import json

from swarmmind.models import ConversationMode, ConversationRuntimeOptions
from swarmmind.services.stream_events import (
    general_agent_status_labels,
    serialize_stream_event,
    task_card_title,
    task_status_from_result,
    tool_activity_label,
    translate_general_agent_event,
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


def test_general_agent_status_labels_by_mode():
    assert general_agent_status_labels(_opts(ConversationMode.ULTRA, thinking=True, subagent=True)) == (
        "Agent Team 正在判断这轮探索需要怎样的协作方式",
        "Agent Team 正在协作处理你的问题",
    )
    assert general_agent_status_labels(_opts(ConversationMode.PRO, thinking=True, subagent=False)) == (
        "正在规划这轮任务的执行方式",
        "正在按规划生成结果",
    )
    assert general_agent_status_labels(_opts(ConversationMode.THINKING, thinking=True, subagent=False)) == (
        "正在分析你的问题",
        "正在整理深入回复",
    )
    assert general_agent_status_labels(_opts(ConversationMode.FLASH, thinking=False, subagent=False)) == (
        "正在准备快速回复",
        "正在快速生成结果",
    )


def test_translate_reasoning_and_assistant_message_respects_runtime_flags():
    flash = _opts(ConversationMode.FLASH, thinking=False, subagent=False)
    thinking = _opts(ConversationMode.THINKING, thinking=True, subagent=False)

    assert (
        translate_general_agent_event(
            {"type": "assistant_reasoning", "message_id": "r1", "content": "thinking..."},
            flash,
        )
        == []
    )

    reasoning_lines = translate_general_agent_event(
        {"type": "assistant_reasoning", "message_id": "r1", "content": "thinking..."},
        thinking,
    )
    assert json.loads(reasoning_lines[0]) == {"type": "thinking", "message_id": "r1", "content": "thinking..."}

    assistant_lines = translate_general_agent_event(
        {"type": "assistant_message", "message_id": "a1", "content": "answer"},
        flash,
    )
    assert json.loads(assistant_lines[0]) == {"type": "assistant_message", "message_id": "a1", "content": "answer"}


def test_translate_tool_calls_and_tool_results_for_ultra_mode():
    ultra = _opts(ConversationMode.ULTRA, thinking=True, subagent=True, plan_mode=True)

    tool_call_lines = translate_general_agent_event(
        {
            "type": "assistant_tool_calls",
            "tool_calls": [
                {"name": "task", "args": {"description": "收集竞品资料"}, "id": "task-1"},
                {"name": "search", "args": {"query": "crm mvp"}, "id": "search-1"},
            ],
        },
        ultra,
    )
    task_line = json.loads(tool_call_lines[0])
    activity_line = json.loads(tool_call_lines[1])
    assert task_line["type"] == "team_task"
    assert task_line["task"]["id"] == "task-1"
    assert task_line["task"]["status"] == "running"
    assert activity_line["type"] == "team_activity"
    assert activity_line["activity"]["id"] == "search-1"
    assert activity_line["activity"]["status"] == "running"

    task_result = translate_general_agent_event(
        {
            "type": "tool_result",
            "tool_name": "task",
            "tool_call_id": "task-1",
            "content": "Task Succeeded. Result: 已完成",
        },
        ultra,
    )
    parsed_task_result = json.loads(task_result[0])
    assert parsed_task_result["type"] == "team_task"
    assert parsed_task_result["task"]["status"] == "completed"
    assert parsed_task_result["task"]["detail"] == "已完成"

    activity_result = translate_general_agent_event(
        {
            "type": "tool_result",
            "tool_name": "search",
            "tool_call_id": "search-1",
            "content": "找到了 5 个相关来源",
        },
        ultra,
    )
    parsed_activity_result = json.loads(activity_result[0])
    assert parsed_activity_result["type"] == "team_activity"
    assert parsed_activity_result["activity"]["id"] == "search-1"
    assert parsed_activity_result["activity"]["status"] == "completed"
    assert parsed_activity_result["activity"]["detail"] == "找到了 5 个相关来源"


def test_translate_clarification_and_custom_events():
    flash = _opts(ConversationMode.FLASH, thinking=False, subagent=False)
    ultra = _opts(ConversationMode.ULTRA, thinking=True, subagent=True, plan_mode=True)

    clarification_lines = translate_general_agent_event(
        {
            "type": "tool_result",
            "tool_name": "ask_clarification",
            "tool_call_id": "clarify-1",
            "content": "请提供目标用户信息",
        },
        flash,
    )
    assert json.loads(clarification_lines[0]) == {
        "type": "clarification_request",
        "clarification": {"id": "clarify-1", "content": "请提供目标用户信息"},
    }

    started = translate_general_agent_event(
        {"type": "custom_event", "event_type": "task_started", "task_id": "t1", "description": "desc"},
        ultra,
    )
    running = translate_general_agent_event(
        {"type": "custom_event", "event_type": "task_running", "task_id": "t1", "message": "working"},
        ultra,
    )
    completed = translate_general_agent_event(
        {"type": "custom_event", "event_type": "task_completed", "task_id": "t1", "result": "ok"},
        ultra,
    )
    failed = translate_general_agent_event(
        {"type": "custom_event", "event_type": "task_failed", "task_id": "t1", "error": "boom"},
        ultra,
    )

    assert json.loads(started[0])["type"] == "task_started"
    assert json.loads(running[0])["type"] == "task_running"
    assert json.loads(completed[0])["type"] == "task_completed"
    assert json.loads(failed[0])["type"] == "task_failed"
