"""Tests for Agent Team API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from swarmmind.api.supervisor import app
from swarmmind.db import init_db, seed_builtin_agent_teams
from swarmmind.repositories.agent_team import AgentTeamRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SWARMMIND_DB_INIT_MODE", "create_all")
    init_db()
    seed_builtin_agent_teams()


def test_list_agent_teams():
    response = client.get("/agent-teams")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3
    names = {t["name"] for t in data["items"]}
    assert "软件开发 Team" in names


def test_get_agent_team():
    repo = AgentTeamRepository()
    teams = repo.list_all(include_disabled=False)
    team_id = teams[0].team_id

    response = client.get(f"/agent-teams/{team_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["team_id"] == team_id
    assert "roles" in data


def test_get_agent_team_not_found():
    response = client.get("/agent-teams/nonexistent")
    assert response.status_code == 404


def test_create_agent_team():
    response = client.post(
        "/agent-teams",
        json={
            "name": "Custom Team",
            "description": "A custom team",
            "icon": "🔧",
            "roles": [{"role_id": "builder", "name": "Builder"}],
            "default_skills": ["build"],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Custom Team"
    assert data["is_builtin"] is False


def test_update_agent_team():
    repo = AgentTeamRepository()
    team = repo.create(name="Before")

    response = client.patch(
        f"/agent-teams/{team.team_id}",
        json={
            "name": "After",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "After"


def test_delete_agent_team():
    repo = AgentTeamRepository()
    team = repo.create(name="To Delete")

    response = client.delete(f"/agent-teams/{team.team_id}")
    assert response.status_code == 204

    # Should be excluded from list
    response = client.get("/agent-teams")
    data = response.json()
    names = {t["name"] for t in data["items"]}
    assert "To Delete" not in names
