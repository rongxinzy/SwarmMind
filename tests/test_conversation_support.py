"""Tests for conversation support service helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace

from swarmmind.services.conversation_support import ConversationSupportService


@dataclass
class FakeConversation:
    id: str = "conv-1"
    title: str = "New Conversation"
    title_status: str = "pending"
    title_source: str | None = None
    title_generated_at: datetime | None = None
    runtime_profile_id: str | None = None
    runtime_instance_id: str | None = None
    thread_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FakeConversationRepo:
    def __init__(self, conversation: FakeConversation | None = None):
        self.conversation = conversation or FakeConversation()
        self.touched_ids: list[str] = []
        self.updated_titles: list[tuple[str, str, str, str | None]] = []

    def get_by_id(self, conversation_id: str):
        return self.conversation

    def touch(self, conversation_id: str) -> None:
        self.touched_ids.append(conversation_id)

    def update_title(self, conversation_id: str, title: str, title_status: str, title_source: str | None) -> None:
        self.updated_titles.append((conversation_id, title, title_status, title_source))


class FakeMessageRepo:
    def __init__(self, messages: list[SimpleNamespace] | None = None):
        self.messages = messages or []
        self.create_calls: list[tuple[str, str, str]] = []

    def create(self, conversation_id: str, role: str, content: str):
        self.create_calls.append((conversation_id, role, content))
        return SimpleNamespace(
            id="msg-created",
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_call_id=None,
            name=None,
            created_at=datetime(2026, 1, 1, 0, 0, 0),
        )

    def list_by_conversation(self, conversation_id: str):
        return self.messages


def test_db_to_message_maps_tool_fields() -> None:
    service = ConversationSupportService(
        conversation_repo=FakeConversationRepo(),
        message_repo=FakeMessageRepo(),
    )
    row = SimpleNamespace(
        id="msg-1",
        conversation_id="conv-1",
        role="tool",
        content="clarification response",
        tool_call_id="tool-123",
        name="ask_clarification_response",
        created_at=datetime(2026, 1, 1, 0, 0, 0),
    )

    message = service.db_to_message(row)

    assert message.id == "msg-1"
    assert message.role == "tool"
    assert message.tool_call_id == "tool-123"
    assert message.name == "ask_clarification_response"


def test_persist_user_message_creates_and_touches_conversation() -> None:
    conversation_repo = FakeConversationRepo()
    message_repo = FakeMessageRepo()
    service = ConversationSupportService(
        conversation_repo=conversation_repo,
        message_repo=message_repo,
    )

    saved = service.persist_user_message("conv-1", "hello")

    assert saved.role == "user"
    assert message_repo.create_calls == [("conv-1", "user", "hello")]
    assert conversation_repo.touched_ids == ["conv-1"]


def test_maybe_generate_conversation_title_generates_only_for_first_exchange() -> None:
    conversation_repo = FakeConversationRepo(conversation=FakeConversation(title_status="pending"))
    message_repo = FakeMessageRepo(
        messages=[
            SimpleNamespace(role="user", content="first user"),
            SimpleNamespace(role="assistant", content="first assistant"),
        ],
    )
    calls: list[tuple[str, str]] = []

    def fake_title_generator(user: str, assistant: str) -> tuple[str, str]:
        calls.append((user, assistant))
        return "Generated Title", "llm"

    service = ConversationSupportService(
        conversation_repo=conversation_repo,
        message_repo=message_repo,
        title_generator=fake_title_generator,
    )

    service.maybe_generate_conversation_title("conv-1")

    assert calls == [("first user", "first assistant")]
    assert conversation_repo.updated_titles == [("conv-1", "Generated Title", "generated", "llm")]


def test_maybe_generate_conversation_title_skips_non_pending_or_non_first_exchange() -> None:
    conversation_repo = FakeConversationRepo(conversation=FakeConversation(title_status="generated"))
    message_repo = FakeMessageRepo(
        messages=[
            SimpleNamespace(role="user", content="u1"),
            SimpleNamespace(role="assistant", content="a1"),
        ],
    )
    service = ConversationSupportService(
        conversation_repo=conversation_repo,
        message_repo=message_repo,
        title_generator=lambda *_: ("should-not-run", "llm"),
    )
    service.maybe_generate_conversation_title("conv-1")
    assert conversation_repo.updated_titles == []

    conversation_repo2 = FakeConversationRepo(conversation=FakeConversation(title_status="pending"))
    message_repo2 = FakeMessageRepo(
        messages=[
            SimpleNamespace(role="user", content="u1"),
            SimpleNamespace(role="user", content="u2"),
            SimpleNamespace(role="assistant", content="a1"),
        ],
    )
    service2 = ConversationSupportService(
        conversation_repo=conversation_repo2,
        message_repo=message_repo2,
        title_generator=lambda *_: ("should-not-run", "llm"),
    )
    service2.maybe_generate_conversation_title("conv-1")
    assert conversation_repo2.updated_titles == []


def test_maybe_generate_conversation_title_uses_fallback_status_for_non_llm_source() -> None:
    conversation_repo = FakeConversationRepo(conversation=FakeConversation(title_status="pending"))
    message_repo = FakeMessageRepo(
        messages=[
            SimpleNamespace(role="user", content="u1"),
            SimpleNamespace(role="assistant", content="a1"),
        ],
    )
    service = ConversationSupportService(
        conversation_repo=conversation_repo,
        message_repo=message_repo,
        title_generator=lambda *_: ("fallback title", "fallback"),
    )

    service.maybe_generate_conversation_title("conv-1")

    assert conversation_repo.updated_titles == [("conv-1", "fallback title", "fallback", "fallback")]
