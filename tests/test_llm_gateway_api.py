"""Tests for LLM Gateway OpenAI-compatible endpoints."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from swarmmind.api.supervisor import app
from swarmmind.db import init_db
from swarmmind.llm_gateway.models import ChatCompletionRequest, ChatMessage
from swarmmind.llm_gateway.router import LlmGateway

client = TestClient(app)


@pytest.fixture(autouse=True)
def _fresh_db(monkeypatch, tmp_path):
    db_path = tmp_path / "llm_gateway_api_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    init_db()


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
    resp = client.post(
        "/gateway/v1/chat/completions",
        json={
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Hi"}],
        },
    )
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
    resp = client.post(
        "/gateway/v1/chat/completions",
        json={
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Hi"}],
            "stream": False,
        },
        headers=_auth_header(),
    )
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_gateway_non_streaming_drops_unsupported_provider_params():
    captured_kwargs: dict = {}

    class FakeRouter:
        async def acompletion(self, **kwargs):
            captured_kwargs.update(kwargs)
            message = SimpleNamespace(role="assistant", content="pong")
            choice = SimpleNamespace(message=message, finish_reason="stop")
            return SimpleNamespace(id="chatcmpl-test", choices=[choice], usage=None)

    gateway = LlmGateway.__new__(LlmGateway)
    gateway._router = FakeRouter()
    gateway._model_names = {"kimi-for-coding"}

    response = await gateway.chat_completions(
        ChatCompletionRequest(
            model="kimi-for-coding",
            messages=[ChatMessage(role="user", content="ping")],
        )
    )

    assert response.choices[0].message.content == "pong"
    assert captured_kwargs["drop_params"] is True


@pytest.mark.asyncio
async def test_gateway_streaming_closes_sse_when_upstream_interrupts():
    class FakeRouter:
        async def acompletion(self, **_kwargs):
            async def stream():
                yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="partial"))])
                raise httpx.RemoteProtocolError("peer closed connection without sending complete message body")

            return stream()

    gateway = LlmGateway.__new__(LlmGateway)
    gateway._router = FakeRouter()
    gateway._model_names = {"kimi-for-coding"}

    lines = [
        line
        async for line in gateway.chat_completions_stream(
            ChatCompletionRequest(
                model="kimi-for-coding",
                messages=[ChatMessage(role="user", content="ping")],
                stream=True,
            )
        )
    ]

    assert "partial" in "".join(lines)
    assert "上游模型流式连接中断" in "".join(lines)
    assert lines[-1] == "data: [DONE]\n\n"
