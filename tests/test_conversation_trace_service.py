"""Tests for conversation-scoped trace orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from swarmmind.services.conversation_trace_service import ConversationTraceService


@dataclass
class FakeConversation:
    thread_id: str | None = None


class FakeConversationRepo:
    def __init__(self, conversation: FakeConversation) -> None:
        self._conversation = conversation
        self.calls: list[str] = []

    def get_by_id(self, conversation_id: str) -> FakeConversation:
        self.calls.append(conversation_id)
        return self._conversation


class FakeTraceReader:
    def __init__(self, response: dict | None = None, error: Exception | None = None) -> None:
        self._response = response or {"thread_id": "resolved-thread", "status": "completed", "events": [], "summary": "ok", "checkpoint_count": 1}
        self._error = error
        self.calls: list[str] = []

    def get_conversation_trace(self, thread_id: str) -> dict:
        self.calls.append(thread_id)
        if self._error is not None:
            raise self._error
        return self._response

    def build_error_trace(self, thread_id: str, summary: str) -> dict:
        return {"thread_id": thread_id, "status": "error", "events": [], "summary": summary, "checkpoint_count": 0}


def test_get_trace_prefers_conversation_thread_id() -> None:
    repo = FakeConversationRepo(FakeConversation(thread_id="runtime-thread"))
    reader = FakeTraceReader()
    service = ConversationTraceService(conversation_repo=repo, trace_reader=reader)

    trace = service.get_trace("conversation-1")

    assert repo.calls == ["conversation-1"]
    assert reader.calls == ["runtime-thread"]
    assert trace["status"] == "completed"


def test_get_trace_falls_back_to_conversation_id_when_thread_missing() -> None:
    repo = FakeConversationRepo(FakeConversation(thread_id=None))
    reader = FakeTraceReader(response={"thread_id": "conversation-2", "status": "empty", "events": [], "summary": "暂无执行记录", "checkpoint_count": 0})
    service = ConversationTraceService(conversation_repo=repo, trace_reader=reader)

    trace = service.get_trace("conversation-2")

    assert reader.calls == ["conversation-2"]
    assert trace["thread_id"] == "conversation-2"


def test_get_trace_returns_error_payload_on_trace_failure() -> None:
    repo = FakeConversationRepo(FakeConversation(thread_id="runtime-thread"))
    reader = FakeTraceReader(error=RuntimeError("checkpoint store offline"))
    service = ConversationTraceService(conversation_repo=repo, trace_reader=reader)

    trace = service.get_trace("conversation-3")

    assert reader.calls == ["runtime-thread"]
    assert trace == {
        "thread_id": "runtime-thread",
        "status": "error",
        "events": [],
        "summary": "读取轨迹失败: checkpoint store offline",
        "checkpoint_count": 0,
    }
