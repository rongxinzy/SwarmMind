"""Tests for runtime model catalog bootstrap and anonymous model resolution."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from swarmmind.api import supervisor
from swarmmind.db import get_connection, init_db, seed_default_agents
from swarmmind.models import SendMessageRequest
from swarmmind.runtime.catalog import (
    ANONYMOUS_SUBJECT_ID,
    ANONYMOUS_SUBJECT_TYPE,
    list_models_for_subject,
    sync_env_runtime_model,
)


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("SWARMMIND_DB_PATH", db_path)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "qwen3.5-plus")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    init_db()
    seed_default_agents()
    yield


def test_sync_env_runtime_model_persists_catalog_and_default_assignment():
    synced_model = sync_env_runtime_model()

    assert synced_model.name == "qwen3.5-plus"
    assert synced_model.provider == "openai"
    assert synced_model.api_key_env_var == "OPENAI_API_KEY"

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM runtime_models WHERE name = ?", (synced_model.name,))
        model_row = cursor.fetchone()
        cursor.execute(
            """
            SELECT * FROM runtime_model_assignments
            WHERE subject_type = ? AND subject_id = ? AND model_name = ?
            """,
            (ANONYMOUS_SUBJECT_TYPE, ANONYMOUS_SUBJECT_ID, synced_model.name),
        )
        assignment_row = cursor.fetchone()
    finally:
        conn.close()

    assert model_row is not None
    assert model_row["enabled"] == 1
    assert model_row["source"] == "env"
    assert assignment_row is not None
    assert assignment_row["is_default"] == 1


def test_list_runtime_models_endpoint_returns_visitor_default():
    response = supervisor.list_runtime_models()

    assert response.default_model == "qwen3.5-plus"
    assert response.subject_type == ANONYMOUS_SUBJECT_TYPE
    assert response.subject_id == ANONYMOUS_SUBJECT_ID
    assert [model.name for model in response.models] == ["qwen3.5-plus"]
    assert response.models[0].is_default is True


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
