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


def test_member_add_command(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/projects/proj-1/members"
        payload = json.loads(request.content.decode())
        assert payload["member_id"] == "user-1"
        assert payload["role"] == "approver"
        return httpx.Response(
            201,
            json={
                "membership_id": "mem-1",
                "project_id": "proj-1",
                "member_id": "user-1",
                "display_name": None,
                "role": "approver",
                "status": "active",
                "capabilities": ["view_project", "approve_high_risk"],
                "created_at": "2026-05-17T00:00:00",
                "updated_at": "2026-05-17T00:00:00",
            },
        )

    _patch_httpx_client(monkeypatch, handler)

    result = runner.invoke(
        app,
        ["--api-url", "http://swarmmind.test", "--json", "member", "add", "proj-1", "user-1", "--role", "approver"],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["role"] == "approver"


def test_member_permission_command(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/projects/proj-1/members/user-1/permissions/run_project"
        return httpx.Response(
            200,
            json={
                "project_id": "proj-1",
                "member_id": "user-1",
                "capability": "run_project",
                "allowed": True,
                "role": "editor",
                "reason": "allowed",
            },
        )

    _patch_httpx_client(monkeypatch, handler)

    result = runner.invoke(
        app,
        ["--api-url", "http://swarmmind.test", "--json", "member", "can", "proj-1", "user-1", "run_project"],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["allowed"] is True


def test_user_create_command(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/users"
        payload = json.loads(request.content.decode())
        assert payload["email"] == "ada@example.com"
        assert payload["password"] == "correct horse"  # noqa: S105 - test fixture password.
        return httpx.Response(
            201,
            json={
                "user_id": "user-1",
                "email": "ada@example.com",
                "display_name": "Ada",
                "role": "admin",
                "status": "active",
                "created_at": "2026-05-17T00:00:00",
                "updated_at": "2026-05-17T00:00:00",
                "last_login_at": None,
            },
        )

    _patch_httpx_client(monkeypatch, handler)

    result = runner.invoke(
        app,
        [
            "--api-url",
            "http://swarmmind.test",
            "--json",
            "user",
            "create",
            "ada@example.com",
            "--password",
            "correct horse",
            "--display-name",
            "Ada",
            "--role",
            "admin",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["user_id"] == "user-1"


def test_auth_me_sends_bearer_token(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/auth/me"
        assert request.headers["authorization"] == "Bearer swm_test"
        return httpx.Response(
            200,
            json={
                "authenticated": True,
                "token_id": "token-1",
                "user": {
                    "user_id": "user-1",
                    "email": "ada@example.com",
                    "display_name": "Ada",
                    "role": "member",
                    "status": "active",
                    "created_at": "2026-05-17T00:00:00",
                    "updated_at": "2026-05-17T00:00:00",
                    "last_login_at": None,
                },
            },
        )

    _patch_httpx_client(monkeypatch, handler)

    result = runner.invoke(
        app, ["--api-url", "http://swarmmind.test", "--api-token", "swm_test", "--json", "auth", "me"]
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["token_id"] == "token-1"  # noqa: S105 - test fixture token ID.
