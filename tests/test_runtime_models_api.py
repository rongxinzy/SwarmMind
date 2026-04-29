"""Runtime models API endpoint tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from swarmmind.api.supervisor import app
from swarmmind.db import dispose_engines, init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("LLM_MODEL", "qwen3.5-plus")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    dispose_engines()
    init_db()


class TestRuntimeModelsEndpoint:
    """Tests for GET /runtime/models and GET /models."""

    def test_get_runtime_models_returns_capability_tags(self):
        response = client.get("/runtime/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert len(data["models"]) >= 1
        model = data["models"][0]
        assert "capability_tags" in model
        assert isinstance(model["capability_tags"], list)

    def test_get_runtime_models_default_vision_tag(self):
        """Default config has vision=true, thinking=false → ['vision']."""
        response = client.get("/runtime/models")
        assert response.status_code == 200
        data = response.json()
        model = data["models"][0]
        assert model["capability_tags"] == ["vision"]

    def test_get_runtime_models_thinking_tag(self, monkeypatch):
        """When LLM_SUPPORTS_THINKING=true, tags include deep + planning + vision."""
        monkeypatch.setenv("LLM_SUPPORTS_THINKING", "true")
        response = client.get("/runtime/models")
        assert response.status_code == 200
        data = response.json()
        model = data["models"][0]
        assert model["capability_tags"] == ["deep", "planning", "vision"]

    def test_get_runtime_models_fast_tag(self, monkeypatch):
        """When both vision and thinking are disabled → ['fast']."""
        monkeypatch.setenv("LLM_SUPPORTS_VISION", "false")
        monkeypatch.setenv("LLM_SUPPORTS_THINKING", "false")
        response = client.get("/runtime/models")
        assert response.status_code == 200
        data = response.json()
        model = data["models"][0]
        assert model["capability_tags"] == ["fast"]

    def test_get_models_alias_returns_same_result(self):
        """GET /models is an alias for GET /runtime/models."""
        response_models = client.get("/models")
        response_runtime = client.get("/runtime/models")
        assert response_models.status_code == 200
        assert response_runtime.status_code == 200
        assert response_models.json() == response_runtime.json()
