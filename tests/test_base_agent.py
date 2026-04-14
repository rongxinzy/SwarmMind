from __future__ import annotations

import pytest

from swarmmind.agents.base import AgentError, BaseAgent
from swarmmind.models import MemoryContext, MemoryLayer


class _FakeLayeredMemory:
    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id


class _DummyAgent(BaseAgent):
    @property
    def domain_tags(self) -> list[str]:
        return [self.domain]


def test_base_agent_loads_system_prompt_from_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class _FakeAgentRepository:
        def get_system_prompt(self, agent_id: str) -> str | None:
            calls.append(agent_id)
            return "system prompt from repository"

    monkeypatch.setattr("swarmmind.agents.base.LayeredMemory", _FakeLayeredMemory)
    monkeypatch.setattr("swarmmind.agents.base.AgentRepository", _FakeAgentRepository)

    agent = _DummyAgent(agent_id="general", domain="general")

    assert calls == ["general"]
    assert agent._system_prompt == "system prompt from repository"
    assert agent.memory.agent_id == "general"


def test_base_agent_raises_for_missing_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeAgentRepository:
        def get_system_prompt(self, agent_id: str) -> str | None:
            return None

    monkeypatch.setattr("swarmmind.agents.base.LayeredMemory", _FakeLayeredMemory)
    monkeypatch.setattr("swarmmind.agents.base.AgentRepository", _FakeAgentRepository)

    with pytest.raises(AgentError, match="Agent missing not found in database\\."):
        _DummyAgent(agent_id="missing", domain="general")


def test_create_rejected_proposal_delegates_to_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    rejected_calls: list[tuple[str, str]] = []

    class _FakeAgentRepository:
        def get_system_prompt(self, agent_id: str) -> str | None:
            return "prompt"

    class _FakeActionProposalRepository:
        def reject(self, proposal_id: str, description: str) -> None:
            rejected_calls.append((proposal_id, description))

    monkeypatch.setattr("swarmmind.agents.base.LayeredMemory", _FakeLayeredMemory)
    monkeypatch.setattr("swarmmind.agents.base.AgentRepository", _FakeAgentRepository)
    monkeypatch.setattr("swarmmind.agents.base.ActionProposalRepository", _FakeActionProposalRepository)

    agent = _DummyAgent(agent_id="general", domain="general")
    agent._create_rejected_proposal("proposal-123", "runtime failed")

    assert rejected_calls == [("proposal-123", "runtime failed")]


@pytest.mark.parametrize(
    ("ctx", "expected_layer", "expected_scope_id"),
    [
        (
            MemoryContext(user_id="user-1", project_id="project-1", team_id="team-1", session_id="session-1"),
            MemoryLayer.TMP,
            "session-1",
        ),
        (
            MemoryContext(user_id="user-1", project_id="project-1", team_id="team-1"),
            MemoryLayer.TEAM,
            "team-1",
        ),
        (
            MemoryContext(user_id="user-1", project_id="project-1"),
            MemoryLayer.PROJECT,
            "project-1",
        ),
        (
            MemoryContext(user_id="user-1"),
            MemoryLayer.USER_SOUL,
            "user-1",
        ),
    ],
)
def test_resolve_write_scope_uses_most_specific_context(
    monkeypatch: pytest.MonkeyPatch,
    ctx: MemoryContext,
    expected_layer: MemoryLayer,
    expected_scope_id: str,
) -> None:
    class _FakeAgentRepository:
        def get_system_prompt(self, agent_id: str) -> str | None:
            return "prompt"

    monkeypatch.setattr("swarmmind.agents.base.LayeredMemory", _FakeLayeredMemory)
    monkeypatch.setattr("swarmmind.agents.base.AgentRepository", _FakeAgentRepository)

    agent = _DummyAgent(agent_id="general", domain="general")
    scope = agent._resolve_write_scope(ctx)

    assert scope.layer == expected_layer
    assert scope.scope_id == expected_scope_id
