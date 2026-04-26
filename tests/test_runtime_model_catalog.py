"""Tests for runtime model catalog bootstrap and anonymous model resolution."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from swarmmind.api import supervisor
from swarmmind.db import init_db, seed_default_agents
from swarmmind.models import SendMessageRequest
from swarmmind.runtime.catalog import (
    ANONYMOUS_SUBJECT_ID,
    ANONYMOUS_SUBJECT_TYPE,
    infer_env_runtime_model,
    list_models_for_subject,
    sync_env_runtime_model,
)
from swarmmind.runtime.models import RuntimeModel


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "qwen3.5-plus")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    init_db()
    seed_default_agents()
    yield


class TestCapabilityTags:
    """Tests for RuntimeModel.capability_tags property."""

    def test_thinking_only(self):
        model = RuntimeModel(
            name="test-model",
            provider="openai",
            model="test-model",
            model_class="langchain_openai:ChatOpenAI",
            api_key_env_var="OPENAI_API_KEY",
            supports_thinking=True,
            supports_vision=False,
        )
        assert model.capability_tags == ["deep", "planning"]

    def test_vision_only(self):
        model = RuntimeModel(
            name="test-model",
            provider="openai",
            model="test-model",
            model_class="langchain_openai:ChatOpenAI",
            api_key_env_var="OPENAI_API_KEY",
            supports_thinking=False,
            supports_vision=True,
        )
        assert model.capability_tags == ["vision"]

    def test_thinking_and_vision(self):
        model = RuntimeModel(
            name="test-model",
            provider="openai",
            model="test-model",
            model_class="langchain_openai:ChatOpenAI",
            api_key_env_var="OPENAI_API_KEY",
            supports_thinking=True,
            supports_vision=True,
        )
        assert model.capability_tags == ["deep", "planning", "vision"]

    def test_neither(self):
        model = RuntimeModel(
            name="test-model",
            provider="openai",
            model="test-model",
            model_class="langchain_openai:ChatOpenAI",
            api_key_env_var="OPENAI_API_KEY",
            supports_thinking=False,
            supports_vision=False,
        )
        assert model.capability_tags == ["fast"]


class TestInferEnvRuntimeModel:
    """Tests for infer_env_runtime_model() capability flag inference."""

    def test_reads_supports_thinking_true(self, monkeypatch):
        monkeypatch.setenv("LLM_MODEL", "deepseek-r1")
        monkeypatch.setenv("LLM_SUPPORTS_THINKING", "true")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        model = infer_env_runtime_model()
        assert model.supports_thinking is True
        assert model.capability_tags == ["deep", "planning", "vision"]

    def test_reads_supports_thinking_false_by_default(self, monkeypatch):
        monkeypatch.setenv("LLM_MODEL", "gpt-4o")
        monkeypatch.delenv("LLM_SUPPORTS_THINKING", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        model = infer_env_runtime_model()
        assert model.supports_thinking is False
        assert model.capability_tags == ["vision"]

    def test_reads_supports_thinking_with_vision_disabled(self, monkeypatch):
        monkeypatch.setenv("LLM_MODEL", "o1")
        monkeypatch.setenv("LLM_SUPPORTS_THINKING", "1")
        monkeypatch.setenv("LLM_SUPPORTS_VISION", "false")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        model = infer_env_runtime_model()
        assert model.supports_thinking is True
        assert model.supports_vision is False
        assert model.capability_tags == ["deep", "planning"]

    def test_reads_supports_thinking_numeric(self, monkeypatch):
        monkeypatch.setenv("LLM_MODEL", "claude-opus")
        monkeypatch.setenv("LLM_SUPPORTS_THINKING", "yes")
        monkeypatch.setenv("LLM_SUPPORTS_VISION", "0")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        model = infer_env_runtime_model()
        assert model.supports_thinking is True
        assert model.supports_vision is False
        assert model.capability_tags == ["deep", "planning"]


def test_sync_env_runtime_model_persists_catalog_and_default_assignment():
    synced_model = sync_env_runtime_model()

    assert synced_model.name == "qwen3.5-plus"
    assert synced_model.provider == "openai"
    # Under the gateway architecture all models route through the SwarmMind LLM Gateway
    assert synced_model.api_key_env_var == "SWARMMIND_GATEWAY_KEY"

    from swarmmind.db import get_session
    from swarmmind.db_models import RuntimeModelAssignmentDB, RuntimeModelDB

    session = get_session()
    try:
        model_row = session.get(RuntimeModelDB, synced_model.name)
        assignment_row = session.get(
            RuntimeModelAssignmentDB,
            (ANONYMOUS_SUBJECT_TYPE, ANONYMOUS_SUBJECT_ID, synced_model.name),
        )
    finally:
        session.close()

    assert model_row is not None
    assert model_row.enabled == 1
    assert model_row.source == "gateway"
    assert assignment_row is not None
    assert assignment_row.is_default == 1


def test_list_runtime_models_endpoint_returns_visitor_default():
    response = supervisor.list_runtime_models()

    assert response.default_model == "qwen3.5-plus"
    assert response.subject_type == ANONYMOUS_SUBJECT_TYPE
    assert response.subject_id == ANONYMOUS_SUBJECT_ID
    assert [model.name for model in response.models] == ["qwen3.5-plus"]
    assert response.models[0].is_default is True


def test_runtime_models_alias_endpoint_returns_same_result():
    # GET /runtime/models is an alias for GET /models
    response = supervisor.list_runtime_models()
    assert response.default_model == "qwen3.5-plus"
    assert [model.name for model in response.models] == ["qwen3.5-plus"]


def test_resolve_runtime_options_defaults_to_anonymous_model():
    runtime_options = supervisor._resolve_runtime_options(
        SendMessageRequest(content="给我一个默认模型"),
    )

    assert runtime_options.model_name == "qwen3.5-plus"


def test_resolve_runtime_options_rejects_unassigned_model():
    with pytest.raises(HTTPException) as exc_info:
        supervisor._resolve_runtime_options(
            SendMessageRequest(content="切换模型", model_name="deepseek-r1"),
        )

    assert exc_info.value.status_code == 400
    assert "deepseek-r1" in str(exc_info.value.detail)


def test_list_models_for_subject_returns_default_first():
    models = list_models_for_subject()

    assert len(models) == 1
    assert models[0].name == "qwen3.5-plus"
    assert models[0].is_default is True
