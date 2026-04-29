"""Tests for Project Agent Team Instance API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from swarmmind.api.supervisor import app
from swarmmind.db import init_db, seed_builtin_agent_teams
from swarmmind.repositories.agent_team import AgentTeamRepository
from swarmmind.repositories.project import ProjectRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SWARMMIND_DB_INIT_MODE", "create_all")
    init_db()
    seed_builtin_agent_teams()


class TestProjectTeamInstanceAPI:
    def test_attach_team_to_project(self):
        # Create a project
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")

        # Get a built-in team
        team_repo = AgentTeamRepository()
        teams = team_repo.list_all(include_disabled=False)
        team_id = teams[0].team_id

        # Attach team
        response = client.post(
            f"/projects/{proj.project_id}/agent-team",
            json={
                "team_template_id": team_id,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["team_template_id"] == team_id
        assert data["team_name"] == teams[0].name
        assert data["status"] == "active"

    def test_attach_team_duplicate_returns_409(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")

        team_repo = AgentTeamRepository()
        teams = team_repo.list_all(include_disabled=False)
        team_id = teams[0].team_id

        # First attach
        response = client.post(
            f"/projects/{proj.project_id}/agent-team",
            json={
                "team_template_id": team_id,
            },
        )
        assert response.status_code == 201

        # Second attach should fail
        response = client.post(
            f"/projects/{proj.project_id}/agent-team",
            json={
                "team_template_id": team_id,
            },
        )
        assert response.status_code == 409

    def test_get_project_team(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")

        team_repo = AgentTeamRepository()
        teams = team_repo.list_all(include_disabled=False)
        team_id = teams[0].team_id

        client.post(
            f"/projects/{proj.project_id}/agent-team",
            json={
                "team_template_id": team_id,
            },
        )

        response = client.get(f"/projects/{proj.project_id}/agent-team")
        assert response.status_code == 200
        data = response.json()
        assert data["team_template_id"] == team_id

    def test_get_project_team_not_found(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="No Team Project")

        response = client.get(f"/projects/{proj.project_id}/agent-team")
        assert response.status_code == 404

    def test_update_project_team(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")

        team_repo = AgentTeamRepository()
        teams = team_repo.list_all(include_disabled=False)
        team_id = teams[0].team_id

        client.post(
            f"/projects/{proj.project_id}/agent-team",
            json={
                "team_template_id": team_id,
            },
        )

        response = client.patch(
            f"/projects/{proj.project_id}/agent-team",
            json={
                "status": "paused",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"

    def test_detach_team_from_project(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")

        team_repo = AgentTeamRepository()
        teams = team_repo.list_all(include_disabled=False)
        team_id = teams[0].team_id

        client.post(
            f"/projects/{proj.project_id}/agent-team",
            json={
                "team_template_id": team_id,
            },
        )

        response = client.delete(f"/projects/{proj.project_id}/agent-team")
        assert response.status_code == 204

        # Verify detached
        response = client.get(f"/projects/{proj.project_id}/agent-team")
        assert response.status_code == 404

    def test_project_response_includes_agent_team(self):
        proj_repo = ProjectRepository()
        proj = proj_repo.create(title="Test Project")

        team_repo = AgentTeamRepository()
        teams = team_repo.list_all(include_disabled=False)
        team_id = teams[0].team_id

        client.post(
            f"/projects/{proj.project_id}/agent-team",
            json={
                "team_template_id": team_id,
            },
        )

        response = client.get(f"/projects/{proj.project_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["agent_team"] is not None
        assert data["agent_team"]["team_template_id"] == team_id

    def test_project_create_with_team_template(self):
        team_repo = AgentTeamRepository()
        teams = team_repo.list_all(include_disabled=False)
        team_id = teams[0].team_id

        response = client.post(
            "/projects",
            json={
                "title": "Project with Team",
                "team_template_id": team_id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["agent_team"] is not None
        assert data["agent_team"]["team_template_id"] == team_id

    def test_project_without_team_has_null_agent_team(self):
        response = client.post(
            "/projects",
            json={
                "title": "Project without Team",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["agent_team"] is None
