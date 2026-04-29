"""Tests for AgentTeamRepository."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from swarmmind.db import init_db, seed_builtin_agent_teams
from swarmmind.repositories.agent_team import AgentTeamRepository


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    init_db()


class TestAgentTeamRepository:
    def test_create_team(self):
        repo = AgentTeamRepository()
        team = repo.create(
            name="Test Team",
            description="A test team",
            icon="🧪",
            roles=[{"role_id": "tester", "name": "Tester"}],
            default_skills=["testing"],
            runtime_profile_prefs={"mode": "pro"},
        )
        assert team.name == "Test Team"
        assert team.description == "A test team"
        assert team.is_builtin == 0

    def test_get_by_id(self):
        repo = AgentTeamRepository()
        created = repo.create(name="Find Me")
        found = repo.get_by_id(created.team_id)
        assert found.team_id == created.team_id
        assert found.name == "Find Me"

    def test_get_by_id_not_found(self):
        repo = AgentTeamRepository()
        with pytest.raises(HTTPException):
            repo.get_by_id("nonexistent")

    def test_list_all_excludes_disabled(self):
        repo = AgentTeamRepository()
        repo.create(name="Active")
        disabled = repo.create(name="Disabled")
        repo.update(disabled.team_id, is_enabled=False)

        items = repo.list_all(include_disabled=False)
        names = {t.name for t in items}
        assert "Active" in names
        assert "Disabled" not in names

    def test_update_team(self):
        repo = AgentTeamRepository()
        team = repo.create(name="Old Name")
        updated = repo.update(team.team_id, name="New Name")
        assert updated.name == "New Name"

    def test_delete_disables(self):
        repo = AgentTeamRepository()
        team = repo.create(name="To Disable")
        assert repo.delete(team.team_id) is True
        found = repo.get_by_id(team.team_id)
        assert found.is_enabled == 0


class TestSeedBuiltinTeams:
    def test_seed_creates_builtin_teams(self):
        seed_builtin_agent_teams()
        repo = AgentTeamRepository()
        items = repo.list_all(include_disabled=False)
        names = {t.name for t in items}
        assert "软件开发 Team" in names
        assert "数据分析 Team" in names
        assert "运维自动化 Team" in names
