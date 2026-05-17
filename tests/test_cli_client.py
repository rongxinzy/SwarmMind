"""CLI HTTP client tests."""

from __future__ import annotations

import json

import httpx
import pytest

from swarmmind.cli.client import BackendUnavailable, ResourceNotFound, SwarmMindClient
from swarmmind.models import HealthResponse


def _client_with_transport(transport: httpx.MockTransport) -> SwarmMindClient:
    client = SwarmMindClient("http://swarmmind.test")
    client.close()
    client._client = httpx.Client(base_url="http://swarmmind.test", transport=transport)
    return client


def test_health_parses_shared_model() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"status": "ok", "timestamp": "2026-05-17T00:00:00Z"})
    )
    client = _client_with_transport(transport)

    result = client.health()

    assert isinstance(result, HealthResponse)
    assert result.status == "ok"


def test_not_found_maps_to_stable_exit_error() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(404, json={"detail": "missing"}))
    client = _client_with_transport(transport)

    with pytest.raises(ResourceNotFound) as exc_info:
        client.get_project("missing")

    assert exc_info.value.exit_code == 4
    assert exc_info.value.message == "missing"


def test_transport_error_maps_to_backend_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    client = _client_with_transport(httpx.MockTransport(handler))

    with pytest.raises(BackendUnavailable) as exc_info:
        client.health()

    assert exc_info.value.exit_code == 3


def test_stream_parses_ndjson_and_sse_lines() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/conversations/conv-1/messages/stream"
        body = json.loads(request.content.decode())
        assert body["content"] == "hello"
        content = b'{"type":"status","label":"accepted"}\ndata: {"type":"done"}\n'
        return httpx.Response(200, content=content, headers={"content-type": "application/x-ndjson"})

    client = _client_with_transport(httpx.MockTransport(handler))

    events = list(client.stream_message("conv-1", "hello"))

    assert events == [
        {"type": "status", "label": "accepted"},
        {"type": "done"},
    ]
