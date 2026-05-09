"""Integration tests for project execution: stream → RunDB row → MessageDB.run_id.

These tests wire the real RunLifecycleService and ConversationExecutionService
with a fake DeerFlow adapter so they run without a real LLM environment.
"""

from __future__ import annotations

import json

import pytest

from swarmmind.db import dispose_engines, init_db
from swarmmind.models import ConversationRuntimeOptions, Message, SendMessageRequest
from swarmmind.repositories.conversation import ConversationRepository
from swarmmind.repositories.message import MessageRepository
from swarmmind.repositories.project import ProjectRepository
from swarmmind.repositories.run import RunRepository
from swarmmind.services.conversation_execution import ConversationExecutionService
from swarmmind.services.conversation_support import ConversationSupportService
from swarmmind.services.run_context import RunContext
from swarmmind.services.run_lifecycle import RunLifecycleService
from swarmmind.services.stream_events import (
    general_agent_status_labels,
    serialize_stream_event,
    translate_general_agent_event,
)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "project_exec_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    dispose_engines()
    init_db()


# ---- Fakes ----


class FakeRuntimeInstance:
    pass


class FakeRuntimeAdapter:
    """Minimal DeerFlow adapter that yields a single assistant message event."""

    def __init__(self, **_kwargs):
        pass

    def stream_events(self, goal: str, ctx=None, runtime_options=None):
        yield {
            "type": "assistant_message",
            "message_id": "msg-001",
            "content": "Hello from fake runtime.",
        }
        return "Hello from fake runtime.", []


class FakeActionProposalRepo:
    def approve(self, _id: str) -> None:
        pass


def _fake_dispatch(content, *, user_id, session_id, override_situation_tag=None):
    class _Result:
        action_proposal_id = "fake-proposal"

    return _Result()


def _fake_derive_tag(content: str) -> str:
    return "general"


def _fake_record_decision(_id: str, _decision) -> None:
    pass


def _fake_bind_runtime(_conversation_id: str):
    return FakeRuntimeInstance(), "thread-001"


def _fake_format_error(exc: Exception) -> str:
    return f"Error: {exc}"


def _fake_resolve_options(body: SendMessageRequest) -> ConversationRuntimeOptions:
    from swarmmind.models import ConversationMode

    return ConversationRuntimeOptions(
        mode=ConversationMode.FLASH,
        model_name="fake-model",
        thinking_enabled=False,
        subagent_enabled=False,
        plan_mode=False,
    )


class _FakeApprovedDecision:
    pass


# ---- Fixtures ----


@pytest.fixture
def run_repo():
    return RunRepository()


@pytest.fixture
def conversation_repo():
    return ConversationRepository()


@pytest.fixture
def message_repo():
    return MessageRepository()


@pytest.fixture
def project():
    return ProjectRepository().create(title="Execution Test Project")


@pytest.fixture
def conversation(conversation_repo):
    return conversation_repo.create("Exec Chat", "pending")


@pytest.fixture
def lifecycle(run_repo):
    return RunLifecycleService(run_repo=run_repo)


@pytest.fixture
def support(conversation_repo, message_repo):
    return ConversationSupportService(
        conversation_repo=conversation_repo,
        message_repo=message_repo,
        title_generator=lambda u, a: (u[:40], "fallback"),
    )


@pytest.fixture
def execution_service(support, lifecycle):
    return ConversationExecutionService(
        conversation_repo=ConversationRepository(),
        message_repo=MessageRepository(),
        action_proposal_repo=FakeActionProposalRepo(),
        runtime_adapter_cls=FakeRuntimeAdapter,
        dispatch_fn=_fake_dispatch,
        derive_situation_tag_fn=_fake_derive_tag,
        record_supervisor_decision_fn=_fake_record_decision,
        approved_decision=_FakeApprovedDecision(),
        persist_user_message_fn=lambda cid, content, run_id=None: support.persist_user_message(
            cid, content, run_id=run_id
        ),
        persist_assistant_message_fn=support.persist_assistant_message,
        maybe_generate_conversation_title_fn=lambda cid: support.maybe_generate_conversation_title(cid),
        bind_conversation_runtime_fn=_fake_bind_runtime,
        format_runtime_error_fn=_fake_format_error,
        resolve_runtime_options_fn=_fake_resolve_options,
        general_agent_status_labels_fn=general_agent_status_labels,
        translate_general_agent_event_fn=translate_general_agent_event,
        serialize_stream_event_fn=serialize_stream_event,
        db_to_message_fn=support.db_to_message,
        execution_logger=__import__("logging").getLogger(__name__),
        run_lifecycle_service=lifecycle,
    )


# ---- Tests ----


class TestProjectExecutionLifecycle:
    def test_stream_creates_run_row_with_project_id(self, execution_service, project, conversation, run_repo):
        run_ctx = RunContext.for_project(project.project_id, conversation.id)
        events = list(
            execution_service.stream_message(conversation.id, SendMessageRequest(content="go"), run_context=run_ctx)
        )

        assert len(events) > 0

        run = run_repo.get_by_id(run_ctx.run_id)
        assert run.project_id == project.project_id
        assert run.conversation_id == conversation.id
        assert run.status == "completed"

    def test_stream_populates_run_id_on_user_message(self, execution_service, project, conversation, message_repo):
        run_ctx = RunContext.for_project(project.project_id, conversation.id)
        list(
            execution_service.stream_message(conversation.id, SendMessageRequest(content="hello"), run_context=run_ctx)
        )

        messages = message_repo.list_by_conversation(conversation.id)
        user_msgs = [m for m in messages if m.role == "user"]
        assert len(user_msgs) == 1
        assert user_msgs[0].run_id == run_ctx.run_id

    def test_stream_populates_run_id_on_assistant_message(self, execution_service, project, conversation, message_repo):
        run_ctx = RunContext.for_project(project.project_id, conversation.id)
        list(
            execution_service.stream_message(conversation.id, SendMessageRequest(content="hello"), run_context=run_ctx)
        )

        messages = message_repo.list_by_conversation(conversation.id)
        assistant_msgs = [m for m in messages if m.role == "assistant"]
        assert len(assistant_msgs) == 1
        assert assistant_msgs[0].run_id == run_ctx.run_id

    def test_exactly_one_run_row_per_stream(self, execution_service, project, conversation, run_repo):
        run_ctx = RunContext.for_project(project.project_id, conversation.id)
        list(execution_service.stream_message(conversation.id, SendMessageRequest(content="task"), run_context=run_ctx))

        runs = run_repo.list_by_project(project.project_id)
        assert len(runs) == 1

    def test_chat_session_stream_creates_no_run_row(self, execution_service, conversation, run_repo):
        list(execution_service.stream_message(conversation.id, SendMessageRequest(content="hi")))
        runs = run_repo.list_by_conversation(conversation.id)
        assert len(runs) == 0

    def test_stream_events_include_status_and_final(self, execution_service, project, conversation):
        run_ctx = RunContext.for_project(project.project_id, conversation.id)
        raw_events = list(
            execution_service.stream_message(conversation.id, SendMessageRequest(content="work"), run_context=run_ctx)
        )
        parsed = [json.loads(e) for e in raw_events]
        event_types = [e["type"] for e in parsed]

        assert "status" in event_types
        assert "assistant_final" in event_types
        assert "done" in event_types

    def test_run_summary_is_truncated_to_500_chars(self, execution_service, project, conversation, run_repo):
        run_ctx = RunContext.for_project(project.project_id, conversation.id)
        list(
            execution_service.stream_message(conversation.id, SendMessageRequest(content="short"), run_context=run_ctx)
        )

        run = run_repo.get_by_id(run_ctx.run_id)
        if run.summary:
            assert len(run.summary) <= 500

    def test_multiple_project_runs_are_independent(self, execution_service, project, conversation, run_repo):
        ctx1 = RunContext.for_project(project.project_id, conversation.id)
        ctx2 = RunContext.for_project(project.project_id, conversation.id)
        assert ctx1.run_id != ctx2.run_id

        list(execution_service.stream_message(conversation.id, SendMessageRequest(content="a"), run_context=ctx1))
        list(execution_service.stream_message(conversation.id, SendMessageRequest(content="b"), run_context=ctx2))

        runs = run_repo.list_by_project(project.project_id)
        assert len(runs) == 2
        run_ids = {r.run_id for r in runs}
        assert ctx1.run_id in run_ids
        assert ctx2.run_id in run_ids


class TestRunEventsEndpoint:
    """Verify GET /projects/{id}/runs/{run_id}/events returns empty list (no audit yet)."""

    def test_run_events_returns_empty_before_phase3(self, execution_service, project, conversation):
        from fastapi.testclient import TestClient

        from swarmmind.api.supervisor import app

        client = TestClient(app)

        run_ctx = RunContext.for_project(project.project_id, conversation.id)
        list(execution_service.stream_message(conversation.id, SendMessageRequest(content="test"), run_context=run_ctx))

        response = client.get(f"/projects/{project.project_id}/runs/{run_ctx.run_id}/events")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
