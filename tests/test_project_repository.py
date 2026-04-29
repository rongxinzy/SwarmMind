"""Project repository tests."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from swarmmind.db import dispose_engines, init_db
from swarmmind.repositories.conversation import ConversationRepository
from swarmmind.repositories.message import MessageRepository
from swarmmind.repositories.project import ProjectRepository


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    dispose_engines()
    init_db()


class TestProjectRepository:
    """ProjectRepository CRUD tests."""

    def test_create_project(self):
        repo = ProjectRepository()
        proj = repo.create(title="Test Project", goal="Build something")
        assert proj.title == "Test Project"
        assert proj.goal == "Build something"
        assert proj.status == "active"
        assert proj.project_id is not None

    def test_get_by_id(self):
        repo = ProjectRepository()
        created = repo.create(title="Get Me", goal="test")
        fetched = repo.get_by_id(created.project_id)
        assert fetched.project_id == created.project_id
        assert fetched.title == "Get Me"

    def test_get_by_id_missing_raises_404(self):
        repo = ProjectRepository()
        with pytest.raises(HTTPException) as exc:
            repo.get_by_id("nonexistent")
        assert exc.value.status_code == 404

    def test_list_all_orders_by_updated_at_desc(self):
        repo = ProjectRepository()
        repo.create(title="First")
        repo.create(title="Second")
        items = repo.list_all()
        assert len(items) >= 2
        assert items[0].title == "Second"
        assert items[1].title == "First"

    def test_update_project(self):
        repo = ProjectRepository()
        proj = repo.create(title="Old Title")
        updated = repo.update(proj.project_id, title="New Title", status="archived")
        assert updated.title == "New Title"
        assert updated.status == "archived"

    def test_update_missing_raises_404(self):
        repo = ProjectRepository()
        with pytest.raises(HTTPException) as exc:
            repo.update("nonexistent", title="X")
        assert exc.value.status_code == 404

    def test_delete_project(self):
        repo = ProjectRepository()
        proj = repo.create(title="To Delete")
        repo.delete(proj.project_id)
        with pytest.raises(HTTPException) as exc:
            repo.get_by_id(proj.project_id)
        assert exc.value.status_code == 404

    def test_link_conversation(self):
        conv_repo = ConversationRepository()
        msg_repo = MessageRepository()
        proj_repo = ProjectRepository()

        conv = conv_repo.create("Chat Session", "pending")
        msg_repo.create(conv.id, "user", "Hello")
        proj = proj_repo.create(title="Promoted")
        proj_repo.link_conversation(proj.project_id, conv.id)

        conv_refreshed = conv_repo.get_by_id(conv.id)
        assert conv_refreshed.promoted_project_id == proj.project_id
