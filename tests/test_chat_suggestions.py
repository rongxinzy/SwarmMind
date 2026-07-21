"""Tests for DeerFlow-native follow-up suggestion API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from swarmmind.api import chat_routes, supervisor
from swarmmind.db import dispose_engines, init_db
from swarmmind.models import CreateConversationRequest


class FakeSuggestionResponse:
    content = '```json\n["继续梳理范围？", "生成交付清单？", "列出风险？"]\n```'


class FakeSuggestionModel:
    async def ainvoke(self, _messages):
        return FakeSuggestionResponse()


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "suggestions.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    dispose_engines()
    init_db()


def test_parse_json_string_list_accepts_markdown_fence() -> None:
    assert chat_routes._parse_json_string_list('```json\n["a", "b"]\n```') == ["a", "b"]


def test_format_suggestion_conversation_normalizes_roles() -> None:
    messages = [
        chat_routes.SuggestionMessage(role="human", content=" 你好 "),
        chat_routes.SuggestionMessage(role="ai", content=" 可以。 "),
        chat_routes.SuggestionMessage(role="system", content=" note "),
    ]

    assert chat_routes._format_suggestion_conversation(messages) == "User: 你好\nAssistant: 可以。\nsystem: note"


def test_thread_suggestions_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(chat_routes, "_create_suggestion_model", lambda _model_name: FakeSuggestionModel())
    client = TestClient(supervisor.app)
    conversation = supervisor.create_conversation(CreateConversationRequest(title="建议测试"))

    response = client.post(
        f"/api/threads/{conversation.id}/suggestions",
        json={
            "messages": [
                {"role": "user", "content": "帮我做一个项目简报"},
                {"role": "assistant", "content": "已经整理了目标、范围和风险。"},
            ],
            "n": 2,
            "model_name": "test-model",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"suggestions": ["继续梳理范围？", "生成交付清单？"]}


def test_thread_suggestions_returns_empty_on_model_error(monkeypatch) -> None:
    def raise_model(_model_name):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(chat_routes, "_create_suggestion_model", raise_model)
    client = TestClient(supervisor.app)
    conversation = supervisor.create_conversation(CreateConversationRequest(title="建议失败测试"))

    response = client.post(
        f"/api/threads/{conversation.id}/suggestions",
        json={"messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 200
    assert response.json() == {"suggestions": []}
