"""Integration tests for project execution: stream → RunDB row → MessageDB.run_id.

These tests wire the real RunLifecycleService and ConversationExecutionService
with a fake DeerFlow runtime so they run without a real LLM environment.
"""

from __future__ import annotations

import json

import pytest

from swarmmind.db import dispose_engines, init_db
from swarmmind.models import ConversationRuntimeOptions, SendMessageRequest
from swarmmind.repositories.artifact import ArtifactRepository
from swarmmind.repositories.conversation import ConversationRepository
from swarmmind.repositories.message import MessageRepository
from swarmmind.repositories.project import ProjectRepository
from swarmmind.repositories.run import RunRepository
from swarmmind.services.conversation_execution import ConversationExecutionService
from swarmmind.services.conversation_support import ConversationSupportService
from swarmmind.services.run_context import RiskPolicy, RunContext
from swarmmind.services.run_lifecycle import RunLifecycleService
from swarmmind.services.stream_events import (
    deerflow_runtime_status_labels,
    serialize_stream_event,
    translate_deerflow_runtime_event,
)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "project_exec_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    dispose_engines()
    init_db()
    FakeRuntime.init_kwargs = []


# ---- Fakes ----


class FakeRuntimeInstance:
    pass


class FakeRuntime:
    """Minimal DeerFlow runtime that yields a single assistant message event."""

    init_kwargs: list[dict] = []

    def __init__(self, **_kwargs):
        self.__class__.init_kwargs.append(dict(_kwargs))

    def stream_events(self, goal: str, ctx=None, runtime_options=None):
        yield {
            "type": "assistant_message",
            "message_id": "msg-001",
            "content": "Hello from fake runtime.",
        }
        return "Hello from fake runtime.", []


class FakeNativeRuntime:
    """Fake runtime that emits complete native DeerFlow messages."""

    def __init__(self, **_kwargs):
        pass

    def stream_events(self, goal: str, ctx=None, runtime_options=None, native_messages: bool = False):
        assert native_messages is True
        yield {
            "type": "deerflow.message",
            "message": {
                "type": "ai",
                "id": "native-tool-call",
                "content": "",
                "additional_kwargs": {"reasoning_content": "先拆成子任务"},
                "response_metadata": {},
                "tool_calls": [
                    {
                        "name": "task",
                        "args": {"description": "顾客 agent：点单"},
                        "id": "call-task-1",
                        "type": "tool_call",
                    }
                ],
            },
        }
        yield {
            "type": "deerflow.message",
            "message": {
                "type": "tool",
                "id": "native-tool-result",
                "name": "task",
                "content": "Task Succeeded. Result: 已点单",
                "tool_call_id": "call-task-1",
                "status": "success",
                "additional_kwargs": {},
                "response_metadata": {},
            },
        }
        yield {
            "type": "deerflow.message",
            "message": {
                "type": "ai",
                "id": "native-final",
                "content": "final native answer",
                "additional_kwargs": {},
                "response_metadata": {},
            },
        }
        return "final native answer", []


class FakeArtifactRuntime:
    """Fake runtime that emits native artifact-producing events."""

    def __init__(self, **_kwargs):
        pass

    def stream_events(self, goal: str, ctx=None, runtime_options=None, native_messages: bool = False):
        assert native_messages is True
        yield {
            "type": "deerflow.message",
            "message": {
                "type": "ai",
                "id": "native-write",
                "content": "",
                "additional_kwargs": {},
                "response_metadata": {},
                "tool_calls": [
                    {
                        "name": "write_file",
                        "args": {"path": "/mnt/user-data/outputs/report.md"},
                        "id": "call-write",
                        "type": "tool_call",
                    },
                    {
                        "name": "present_files",
                        "args": {
                            "filepaths": [
                                "mnt/user-data/outputs/report.md",
                                "/mnt/user-data/outputs/chart.svg",
                                "/tmp/not-artifact.txt",
                            ]
                        },
                        "id": "call-present",
                        "type": "tool_call",
                    },
                ],
            },
        }
        yield {
            "type": "values",
            "artifacts": [
                "/mnt/user-data/outputs/chart.svg",
                "/mnt/user-data/outputs/table.csv",
            ],
        }
        yield {
            "type": "deerflow.message",
            "message": {
                "type": "ai",
                "id": "native-artifact-final",
                "content": "created artifacts",
                "additional_kwargs": {},
                "response_metadata": {},
            },
        }
        return "created artifacts", []


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
def artifact_repo():
    return ArtifactRepository()


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
def execution_service(support, lifecycle, artifact_repo):
    return ConversationExecutionService(
        conversation_repo=ConversationRepository(),
        message_repo=MessageRepository(),
        runtime_cls=FakeRuntime,
        persist_user_message_fn=lambda cid, content, run_id=None: support.persist_user_message(
            cid, content, run_id=run_id
        ),
        persist_assistant_message_fn=support.persist_assistant_message,
        maybe_generate_conversation_title_fn=support.maybe_generate_conversation_title,
        bind_conversation_runtime_fn=_fake_bind_runtime,
        format_runtime_error_fn=_fake_format_error,
        resolve_runtime_options_fn=_fake_resolve_options,
        deerflow_runtime_status_labels_fn=deerflow_runtime_status_labels,
        translate_deerflow_runtime_event_fn=translate_deerflow_runtime_event,
        serialize_stream_event_fn=serialize_stream_event,
        db_to_message_fn=support.db_to_message,
        execution_logger=__import__("logging").getLogger(__name__),
        run_lifecycle_service=lifecycle,
        artifact_repo=artifact_repo,
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

    def test_stream_persists_native_deerflow_messages(self, execution_service, project, conversation, message_repo):
        execution_service._runtime_cls = FakeNativeRuntime
        run_ctx = RunContext.for_project(project.project_id, conversation.id)
        raw_events = list(
            execution_service.stream_message(conversation.id, SendMessageRequest(content="native"), run_context=run_ctx)
        )
        parsed = [json.loads(e) for e in raw_events]

        messages = message_repo.list_by_conversation(conversation.id)
        native_rows = [m for m in messages if m.native_payload]

        assert [m.native_payload["id"] for m in native_rows] == [
            "native-tool-call",
            "native-tool-result",
            "native-final",
        ]
        assert native_rows[0].native_payload["tool_calls"][0]["name"] == "task"
        assert native_rows[1].tool_call_id == "call-task-1"
        assert native_rows[2].role == "assistant"
        assert native_rows[2].content == "final native answer"
        assert len([m for m in messages if m.role == "assistant" and m.content == "final native answer"]) == 1
        assert next(e for e in parsed if e["type"] == "assistant_final")["message"]["id"] == native_rows[2].id

    def test_native_stream_emits_deerflow_messages_without_auxiliary_events(
        self,
        execution_service,
        project,
        conversation,
        message_repo,
    ):
        execution_service._runtime_cls = FakeNativeRuntime
        run_ctx = RunContext.for_project(project.project_id, conversation.id)
        raw_events = list(
            execution_service.stream_native_message(conversation.id, SendMessageRequest(content="native"), run_context=run_ctx)
        )
        parsed = [json.loads(e) for e in raw_events]
        event_types = [e["type"] for e in parsed]

        assert event_types.count("deerflow.message") == 4
        assert "content.accumulated" not in event_types
        assert "status.thinking" not in event_types
        assert "status.running" not in event_types
        assert "assistant_final" not in event_types
        assert event_types[-2:] == ["title", "done"]
        assert parsed[0]["message"]["type"] == "human"
        assert parsed[-3]["message"]["id"] == "native-final"
        assert parsed[-2]["conversation"]["id"] == conversation.id

        messages = message_repo.list_by_conversation(conversation.id)
        native_rows = [m for m in messages if m.native_payload]
        assert [m.native_payload["id"] for m in native_rows] == [
            "native-tool-call",
            "native-tool-result",
            "native-final",
        ]

    def test_native_stream_falls_back_to_final_ai_message_when_runtime_has_no_native_events(
        self,
        execution_service,
        conversation,
    ):
        raw_events = list(execution_service.stream_native_message(conversation.id, SendMessageRequest(content="native fallback")))
        parsed = [json.loads(e) for e in raw_events]
        event_types = [e["type"] for e in parsed]
        assistant_messages = [
            event["message"]
            for event in parsed
            if event["type"] == "deerflow.message" and event["message"]["type"] == "ai"
        ]

        assert "content.accumulated" not in event_types
        assert "assistant_final" not in event_types
        assert assistant_messages[-1]["content"] == "Hello from fake runtime."

    def test_stream_preserves_native_human_message_metadata(self, execution_service, project, conversation, message_repo):
        run_ctx = RunContext.for_project(project.project_id, conversation.id)
        native_human = {
            "type": "human",
            "content": "review uploaded file",
            "additional_kwargs": {
                "files": [
                    {
                        "filename": "brief.txt",
                        "size": 12,
                        "path": "/mnt/user-data/uploads/brief.txt",
                        "status": "uploaded",
                    }
                ]
            },
            "response_metadata": {},
        }

        raw_events = list(
            execution_service.stream_message(
                conversation.id,
                SendMessageRequest(content="review uploaded file", native_message=native_human),
                run_context=run_ctx,
            )
        )
        parsed = [json.loads(e) for e in raw_events]
        human_event = next(e for e in parsed if e["type"] == "deerflow.message" and e["message"]["type"] == "human")
        messages = message_repo.list_by_conversation(conversation.id)
        user_row = next(m for m in messages if m.role == "user")

        assert human_event["message"]["additional_kwargs"] == native_human["additional_kwargs"]
        assert user_row.native_payload["additional_kwargs"] == native_human["additional_kwargs"]
        assert user_row.native_payload["id"] == user_row.id

    def test_native_stream_registers_deerflow_artifacts(
        self,
        execution_service,
        project,
        conversation,
        artifact_repo,
    ):
        execution_service._runtime_cls = FakeArtifactRuntime
        run_ctx = RunContext.for_project(project.project_id, conversation.id)

        raw_events = list(
            execution_service.stream_native_message(
                conversation.id,
                SendMessageRequest(content="create artifacts"),
                run_context=run_ctx,
            )
        )
        parsed = [json.loads(e) for e in raw_events]

        assert any(event["type"] == "deerflow.message" for event in parsed)
        artifacts = artifact_repo.list_by_conversation(conversation.id)
        by_path = {artifact.path: artifact for artifact in artifacts}

        assert set(by_path) == {
            "/mnt/user-data/outputs/report.md",
            "/mnt/user-data/outputs/chart.svg",
            "/mnt/user-data/outputs/table.csv",
        }
        assert by_path["/mnt/user-data/outputs/report.md"].artifact_type == "write_file"
        assert by_path["/mnt/user-data/outputs/chart.svg"].artifact_type == "present_files"
        assert by_path["/mnt/user-data/outputs/table.csv"].artifact_type == "present_files"
        assert all(artifact.run_id == run_ctx.run_id for artifact in artifacts)

    def test_native_chat_session_registers_artifacts_without_run_id(
        self,
        execution_service,
        conversation,
        artifact_repo,
    ):
        execution_service._runtime_cls = FakeArtifactRuntime

        list(
            execution_service.stream_native_message(
                conversation.id,
                SendMessageRequest(content="create chat artifacts"),
            )
        )

        artifacts = artifact_repo.list_by_conversation(conversation.id)
        assert {artifact.path for artifact in artifacts} == {
            "/mnt/user-data/outputs/report.md",
            "/mnt/user-data/outputs/chart.svg",
            "/mnt/user-data/outputs/table.csv",
        }
        assert all(artifact.run_id is None for artifact in artifacts)

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

    def test_project_runs_do_not_inject_approval_middleware(self, execution_service, project, conversation, run_repo):
        run_ctx = RunContext.for_project(project.project_id, conversation.id, risk_policy=RiskPolicy.STRICT)
        raw_events = list(
            execution_service.stream_message(conversation.id, SendMessageRequest(content="strict"), run_context=run_ctx)
        )
        parsed = [json.loads(e) for e in raw_events]

        run = run_repo.get_by_id(run_ctx.run_id)
        assert run.status == "completed"
        assert "status.waiting_approval" not in [event["type"] for event in parsed]
        assert FakeRuntime.init_kwargs[-1].get("middlewares") is None

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
