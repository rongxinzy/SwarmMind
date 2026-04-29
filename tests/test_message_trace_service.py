"""Tests for MessageTraceService — trace -> TraceSummaryResponse translation."""

from __future__ import annotations

from typing import Any

from swarmmind.models import TraceSummaryResponse
from swarmmind.services.message_trace_service import MessageTraceService


class FakeConversationTraceService:
    """Fake that returns canned trace payloads."""

    def __init__(self, trace: dict[str, Any] | Exception) -> None:
        self._trace = trace

    def get_trace(self, conversation_id: str) -> dict[str, Any]:
        if isinstance(self._trace, Exception):
            raise self._trace
        return self._trace


def _make_service(trace: dict[str, Any] | Exception) -> MessageTraceService:
    return MessageTraceService(conversation_trace_service=FakeConversationTraceService(trace))


def test_empty_trace_returns_degraded_summary() -> None:
    svc = _make_service({"events": [], "summary": "暂无执行记录"})
    result = svc.get_summary("conv-1", "msg-1")

    assert result == TraceSummaryResponse(
        steps_count=0,
        subagent_calls_count=0,
        artifacts_count=0,
        blocked_points=[],
        summary="暂无执行记录",
    )


def test_trace_read_failure_returns_degraded_summary() -> None:
    svc = _make_service(RuntimeError("checkpoint store offline"))
    result = svc.get_summary("conv-1", "msg-1")

    assert result.summary == "执行轨迹暂不可读"
    assert result.steps_count == 0


def test_simple_assistant_response_trace() -> None:
    svc = _make_service(
        {
            "events": [
                {"type": "user_input", "content": "hello"},
                {"type": "assistant_response", "content": "hi there"},
            ],
        }
    )
    result = svc.get_summary("conv-1", "msg-1")

    assert result.steps_count == 1  # assistant_response only
    assert result.subagent_calls_count == 0
    assert result.artifacts_count == 0
    assert result.blocked_points == []
    assert "用户输入 1 轮" in result.summary


def test_subagent_and_tool_calls_counted() -> None:
    svc = _make_service(
        {
            "events": [
                {"type": "user_input"},
                {"type": "subagent_dispatch", "tool_calls": [{"name": "task"}]},
                {"type": "tool_execution", "agent_id": "bash"},
                {"type": "assistant_response"},
            ],
        }
    )
    result = svc.get_summary("conv-1", "msg-1")

    assert result.steps_count == 3  # subagent + tool + assistant
    assert result.subagent_calls_count == 1
    assert result.summary == "用户输入 1 轮 → 子代理协作 1 次，工具调用 1 次"


def test_artifacts_counted() -> None:
    svc = _make_service(
        {
            "events": [
                {"type": "user_input"},
                {"type": "artifact_created", "artifact_path": "/tmp/report.md"},
                {"type": "artifact_created", "artifact_path": "/tmp/plan.md"},
            ],
        }
    )
    result = svc.get_summary("conv-1", "msg-1")

    assert result.artifacts_count == 2
    assert result.steps_count == 2  # both artifacts
    assert "生成产物 2 个" in result.summary


def test_blocked_points_from_clarification() -> None:
    svc = _make_service(
        {
            "events": [
                {"type": "user_input"},
                {"type": "tool_execution", "agent_id": "ask_clarification", "result": "What is your budget?"},
                {"type": "user_input"},
                {"type": "assistant_response"},
            ],
        }
    )
    result = svc.get_summary("conv-1", "msg-1")

    assert len(result.blocked_points) == 1
    assert "请求补充信息" in result.blocked_points[0]
    assert "阻塞点 1 个" in result.summary


def test_blocked_points_from_failed_task() -> None:
    svc = _make_service(
        {
            "events": [
                {"type": "user_input"},
                {"type": "task_failed", "error": "Connection timeout"},
            ],
        }
    )
    result = svc.get_summary("conv-1", "msg-1")

    assert len(result.blocked_points) == 1
    assert "子任务失败" in result.blocked_points[0]
    assert "阻塞点 1 个" in result.summary


def test_todos_updated_counts_as_step() -> None:
    svc = _make_service(
        {
            "events": [
                {"type": "user_input"},
                {"type": "todos_updated", "todos_count": 3, "todo_items": [{"description": "a", "status": "pending"}]},
                {"type": "assistant_response"},
            ],
        }
    )
    result = svc.get_summary("conv-1", "msg-1")

    assert result.steps_count == 2  # todos_updated + assistant_response


def test_multi_turn_summary() -> None:
    svc = _make_service(
        {
            "events": [
                {"type": "user_input"},
                {"type": "user_input"},
                {"type": "subagent_dispatch"},
                {"type": "tool_execution", "agent_id": "search"},
                {"type": "artifact_created"},
                {"type": "assistant_response"},
            ],
        }
    )
    result = svc.get_summary("conv-1", "msg-1")

    assert result.steps_count == 4
    assert result.subagent_calls_count == 1
    assert result.artifacts_count == 1
    assert "用户输入 2 轮" in result.summary
    assert "子代理协作 1 次" in result.summary
    assert "工具调用 1 次" in result.summary
    assert "生成产物 1 个" in result.summary


# ---- extract_artifacts tests ----


class FakeArtifactRepository:
    """Fake artifact repo that records create calls."""

    def __init__(self) -> None:
        self.artifacts: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        artifact = type("FakeArtifact", (), {"artifact_id": f"art-{len(self.artifacts)}", **kwargs})()
        self.artifacts.append(artifact)
        return artifact

    def list_by_conversation(self, _conversation_id: str) -> list[Any]:
        return []


def test_extract_artifacts_from_trace_events() -> None:
    fake_repo = FakeArtifactRepository()
    svc = MessageTraceService(
        conversation_trace_service=FakeConversationTraceService(
            {
                "events": [
                    {
                        "type": "artifact_created",
                        "artifact_path": "/tmp/report.md",
                        "artifact_type": "write_file",
                        "run_id": "run-1",
                        "task_id": "task-1",
                        "author_role": "架构专家",
                    },
                    {"type": "artifact_created", "artifact_path": "/tmp/plan.md", "artifact_type": "present_files"},
                ],
            }
        ),
        artifact_repo=fake_repo,
    )

    created = svc.extract_artifacts("conv-1", project_id="proj-1")

    assert len(created) == 2
    assert created[0]["name"] == "/tmp/report.md"
    assert created[0]["run_id"] == "run-1"
    assert created[0]["task_id"] == "task-1"
    assert created[0]["author_role"] == "架构专家"
    assert created[1]["name"] == "/tmp/plan.md"
    assert created[1]["run_id"] is None
    assert created[1]["task_id"] is None
    assert created[1]["author_role"] is None


def test_extract_artifacts_uses_fallback_params() -> None:
    fake_repo = FakeArtifactRepository()
    svc = MessageTraceService(
        conversation_trace_service=FakeConversationTraceService(
            {
                "events": [
                    {"type": "artifact_created", "artifact_path": "/tmp/design.md"},
                ],
            }
        ),
        artifact_repo=fake_repo,
    )

    created = svc.extract_artifacts(
        "conv-1",
        project_id="proj-1",
        run_id="run-2",
        task_id="task-2",
        author_role="产品专家",
    )

    assert len(created) == 1
    assert created[0]["run_id"] == "run-2"
    assert created[0]["task_id"] == "task-2"
    assert created[0]["author_role"] == "产品专家"


def test_extract_artifacts_skips_duplicates() -> None:
    fake_repo = FakeArtifactRepository()
    svc = MessageTraceService(
        conversation_trace_service=FakeConversationTraceService(
            {
                "events": [
                    {"type": "artifact_created", "artifact_path": "/tmp/report.md"},
                    {"type": "artifact_created", "artifact_path": "/tmp/report.md"},
                ],
            }
        ),
        artifact_repo=fake_repo,
    )

    created = svc.extract_artifacts("conv-1")

    assert len(created) == 1


def test_extract_artifacts_no_repo_returns_empty() -> None:
    svc = MessageTraceService(
        conversation_trace_service=FakeConversationTraceService({"events": []}),
        artifact_repo=None,
    )

    created = svc.extract_artifacts("conv-1")

    assert created == []


def test_extract_artifacts_trace_failure_returns_empty() -> None:
    fake_repo = FakeArtifactRepository()
    svc = MessageTraceService(
        conversation_trace_service=FakeConversationTraceService(RuntimeError("store down")),
        artifact_repo=fake_repo,
    )

    created = svc.extract_artifacts("conv-1")

    assert created == []
