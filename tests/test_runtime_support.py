"""Tests for runtime support helpers extracted from supervisor."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi import HTTPException

from swarmmind.models import ConversationMode, SendMessageRequest
from swarmmind.runtime import RuntimeConfigError, RuntimeExecutionError, RuntimeUnavailableError
from swarmmind.services.runtime_support import (
    RuntimeSupportService,
    conversation_thread_id,
    format_runtime_error,
    normalize_model_name,
)


class FakeConversationRepo:
    def __init__(self) -> None:
        self.update_calls: list[tuple[str, str | None, str | None, str | None]] = []

    def update_runtime(
        self,
        conversation_id: str,
        runtime_profile_id: str | None,
        runtime_instance_id: str | None,
        thread_id: str | None,
    ) -> None:
        self.update_calls.append((conversation_id, runtime_profile_id, runtime_instance_id, thread_id))


@dataclass
class FakeRuntimeInstance:
    runtime_profile_id: str
    runtime_instance_id: str


@dataclass
class FakeModelSelection:
    name: str


def test_normalize_model_name_behavior() -> None:
    assert normalize_model_name(None) is None
    assert normalize_model_name("") is None
    assert normalize_model_name("   ") is None
    assert normalize_model_name("  gpt-4o-mini ") == "gpt-4o-mini"


def test_conversation_thread_id_passthrough() -> None:
    assert conversation_thread_id("conv-123") == "conv-123"


def test_format_runtime_error_behavior() -> None:
    assert format_runtime_error(RuntimeConfigError("bad config")) == "DeerFlow Runtime error: bad config"
    assert format_runtime_error(RuntimeUnavailableError("offline")) == "DeerFlow Runtime error: offline"
    assert format_runtime_error(RuntimeExecutionError("boom")) == "DeerFlow Runtime error: boom"
    assert format_runtime_error(ValueError("unexpected")) == "Unexpected DeerFlow execution error: unexpected"


def test_resolve_model_name_for_request_success_and_params() -> None:
    repo = FakeConversationRepo()
    seen: dict[str, str | None] = {}

    def fake_resolve_model_for_subject(**kwargs):
        seen["requested_model_name"] = kwargs["requested_model_name"]
        seen["subject_type"] = kwargs["subject_type"]
        seen["subject_id"] = kwargs["subject_id"]
        return FakeModelSelection(name="resolved-model")

    service = RuntimeSupportService(
        conversation_repo=repo,  # type: ignore[arg-type]
        resolve_model_for_subject_fn=fake_resolve_model_for_subject,
        subject_type="anon_type",
        subject_id="anon_id",
    )

    model_name = service.resolve_model_name_for_request("  requested-model  ")

    assert model_name == "resolved-model"
    assert seen == {
        "requested_model_name": "requested-model",
        "subject_type": "anon_type",
        "subject_id": "anon_id",
    }


def test_resolve_model_name_for_request_runtime_config_error_status_codes() -> None:
    repo = FakeConversationRepo()

    def fake_resolve_model_for_subject(**_kwargs):
        raise RuntimeConfigError("invalid runtime setup")

    service = RuntimeSupportService(
        conversation_repo=repo,  # type: ignore[arg-type]
        resolve_model_for_subject_fn=fake_resolve_model_for_subject,
    )

    with pytest.raises(HTTPException) as specified_exc:
        service.resolve_model_name_for_request("specified-model")
    assert specified_exc.value.status_code == 400
    assert specified_exc.value.detail == "invalid runtime setup"

    with pytest.raises(HTTPException) as default_exc:
        service.resolve_model_name_for_request("   ")
    assert default_exc.value.status_code == 503
    assert default_exc.value.detail == "invalid runtime setup"


def test_bind_conversation_runtime_updates_repository() -> None:
    repo = FakeConversationRepo()

    def fake_ensure_runtime():
        return FakeRuntimeInstance(
            runtime_profile_id="profile-1",
            runtime_instance_id="instance-1",
        )

    service = RuntimeSupportService(
        conversation_repo=repo,  # type: ignore[arg-type]
        ensure_default_runtime_instance_fn=fake_ensure_runtime,
    )

    runtime_instance, thread_id = service.bind_conversation_runtime("conv-1")

    assert runtime_instance.runtime_profile_id == "profile-1"
    assert runtime_instance.runtime_instance_id == "instance-1"
    assert thread_id == "conv-1"
    assert repo.update_calls == [("conv-1", "profile-1", "instance-1", "conv-1")]


def test_resolve_runtime_options_behavior() -> None:
    repo = FakeConversationRepo()

    def fake_resolve_model_for_subject(**_kwargs):
        return FakeModelSelection(name="resolved-default")

    service = RuntimeSupportService(
        conversation_repo=repo,  # type: ignore[arg-type]
        resolve_model_for_subject_fn=fake_resolve_model_for_subject,
    )

    flash = service.resolve_runtime_options(
        SendMessageRequest(content="hello", reasoning=False, mode=None, model_name=None),
    )
    assert flash.mode == ConversationMode.FLASH
    assert flash.model_name == "resolved-default"
    assert flash.thinking_enabled is False
    assert flash.plan_mode is False
    assert flash.subagent_enabled is False

    thinking = service.resolve_runtime_options(
        SendMessageRequest(content="hello", reasoning=True, mode=None, model_name=None),
    )
    assert thinking.mode == ConversationMode.THINKING
    assert thinking.thinking_enabled is True
    assert thinking.plan_mode is False
    assert thinking.subagent_enabled is False

    ultra = service.resolve_runtime_options(
        SendMessageRequest(content="hello", mode=ConversationMode.ULTRA, model_name="x"),
    )
    assert ultra.mode == ConversationMode.ULTRA
    assert ultra.thinking_enabled is True
    assert ultra.plan_mode is True
    assert ultra.subagent_enabled is True
