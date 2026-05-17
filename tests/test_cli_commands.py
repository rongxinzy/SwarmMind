"""CLI command smoke tests."""

from __future__ import annotations

import json

import httpx
from typer.testing import CliRunner

from swarmmind.cli import client as cli_client
from swarmmind.cli.__main__ import app

runner = CliRunner()


def _patch_httpx_client(monkeypatch, handler) -> None:
    real_client = httpx.Client
    transport = httpx.MockTransport(handler)

    def factory(*args, **kwargs):
        return real_client(*args, transport=transport, **kwargs)

    monkeypatch.setattr(cli_client.httpx, "Client", factory)


def test_health_json_command(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/health"
        return httpx.Response(200, json={"status": "ok", "timestamp": "2026-05-17T00:00:00Z"})

    _patch_httpx_client(monkeypatch, handler)

    result = runner.invoke(app, ["--api-url", "http://swarmmind.test", "--json", "health"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["status"] == "ok"


def test_chat_stream_json_command(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/conversations/conv-1/messages/stream"
        payload = json.loads(request.content.decode())
        assert payload["content"] == "hello world"
        return httpx.Response(
            200,
            content=b'{"type":"status","label":"accepted"}\n{"type":"done"}\n',
            headers={"content-type": "application/x-ndjson"},
        )

    _patch_httpx_client(monkeypatch, handler)

    result = runner.invoke(
        app,
        ["--api-url", "http://swarmmind.test", "--json", "chat", "stream", "conv-1", "hello", "world"],
    )

    assert result.exit_code == 0
    lines = [json.loads(line) for line in result.stdout.splitlines()]
    assert lines == [{"type": "status", "label": "accepted"}, {"type": "done"}]


def test_project_list_limit_command(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/projects"
        assert request.url.params["limit"] == "5"
        assert request.url.params["offset"] == "2"
        return httpx.Response(200, json={"items": [], "total": 0})

    _patch_httpx_client(monkeypatch, handler)

    result = runner.invoke(
        app,
        ["--api-url", "http://swarmmind.test", "--json", "project", "list", "--limit", "5", "--offset", "2"],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {"items": [], "total": 0}
