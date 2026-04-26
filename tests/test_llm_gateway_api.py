"""Tests for LLM Gateway OpenAI-compatible endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from swarmmind.api.supervisor import app
from swarmmind.db import init_orm_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def _fresh_db(monkeypatch, tmp_path):
    db_path = tmp_path / "llm_gateway_api_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SWARMMIND_DB_INIT_MODE", "create_all")
    init_orm_db()


def _auth_header():
    from swarmmind.services.gateway_key import get_gateway_key
    return {"Authorization": f"Bearer {get_gateway_key()}"}


def test_list_models_unauthorized():
    resp = client.get("/gateway/v1/models")
    assert resp.status_code == 401


def test_list_models_with_mocked_gateway(monkeypatch):
    from swarmmind.llm_gateway.models import GatewayModelInfo, GatewayModelListResponse

    mock_gateway = MagicMock()
    mock_gateway.list_models.return_value = GatewayModelListResponse(
        data=[GatewayModelInfo(id="gpt-4o", created=1234567890)]
    )
    monkeypatch.setattr(
        "swarmmind.api.llm_gateway_routes.get_gateway",
        lambda: mock_gateway,
    )
    resp = client.get("/gateway/v1/models", headers=_auth_header())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == "gpt-4o"


def test_chat_completions_unauthorized():
    resp = client.post("/gateway/v1/chat/completions", json={
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "Hi"}],
    })
    assert resp.status_code == 401


def test_chat_completions_no_router(monkeypatch):
    mock_gateway = MagicMock()
    mock_gateway.chat_completions.side_effect = RuntimeError(
        "Gateway router is not available. No providers configured."
    )
    monkeypatch.setattr(
        "swarmmind.api.llm_gateway_routes.get_gateway",
        lambda: mock_gateway,
    )
    resp = client.post("/gateway/v1/chat/completions", json={
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "Hi"}],
        "stream": False,
    }, headers=_auth_header())
    assert resp.status_code == 503
