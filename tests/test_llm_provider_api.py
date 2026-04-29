"""Tests for LLM Provider management API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from swarmmind.api.supervisor import app
from swarmmind.db import init_orm_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def _fresh_db(monkeypatch, tmp_path):
    db_path = tmp_path / "llm_provider_api_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SWARMMIND_DB_INIT_MODE", "create_all")
    init_orm_db()


def test_create_provider():
    resp = client.post(
        "/llm-providers",
        json={
            "name": "OpenAI Test",
            "provider_type": "openai",
            "api_key": "sk-test-key",
            "base_url": "https://api.openai.com/v1",
            "models": [
                {"model_name": "gpt-4o", "litellm_model": "openai/gpt-4o", "supports_vision": True},
            ],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "OpenAI Test"
    assert data["provider_type"] == "openai"
    assert data["base_url"] == "https://api.openai.com/v1"
    assert len(data["models"]) == 1
    assert data["models"][0]["model_name"] == "gpt-4o"


def test_list_providers():
    client.post(
        "/llm-providers",
        json={
            "name": "A",
            "provider_type": "openai",
            "api_key": "sk-a",
        },
    )
    client.post(
        "/llm-providers",
        json={
            "name": "B",
            "provider_type": "anthropic",
            "api_key": "sk-b",
        },
    )
    resp = client.get("/llm-providers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


def test_get_provider():
    created = client.post(
        "/llm-providers",
        json={
            "name": "Test",
            "provider_type": "openai",
            "api_key": "sk-xxx",
        },
    ).json()
    resp = client.get(f"/llm-providers/{created['provider_id']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test"


def test_get_provider_not_found():
    resp = client.get("/llm-providers/nonexistent")
    assert resp.status_code == 404


def test_update_provider():
    created = client.post(
        "/llm-providers",
        json={
            "name": "Old",
            "provider_type": "openai",
            "api_key": "sk-old",
        },
    ).json()
    resp = client.patch(
        f"/llm-providers/{created['provider_id']}",
        json={
            "name": "New",
            "base_url": "https://new.example.com",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New"
    assert data["base_url"] == "https://new.example.com"


def test_delete_provider():
    created = client.post(
        "/llm-providers",
        json={
            "name": "ToDelete",
            "provider_type": "openai",
            "api_key": "sk-del",
        },
    ).json()
    resp = client.delete(f"/llm-providers/{created['provider_id']}")
    assert resp.status_code == 204

    # Should be excluded from list
    list_resp = client.get("/llm-providers")
    assert list_resp.json()["total"] == 0


def test_gateway_key_endpoint():
    resp = client.get("/gateway/key")
    assert resp.status_code == 200
    data = resp.json()
    assert data["gateway_key"].startswith("sk-swarmmind-")
    assert "/gateway/v1" in data["gateway_base_url"]
