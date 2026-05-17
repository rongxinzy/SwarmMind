"""Read-only memory API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from swarmmind.api.supervisor import app
from swarmmind.db import dispose_engines, init_db
from swarmmind.models import MemoryLayer, MemoryScope
from swarmmind.repositories.memory import MemoryRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "memory_api_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    dispose_engines()
    init_db()


def test_get_memory_entry_by_scope() -> None:
    repo = MemoryRepository()
    repo.write(
        MemoryScope(layer=MemoryLayer.PROJECT, scope_id="proj-1"),
        key="decision",
        value="ship",
        tags=["release"],
        ttl=None,
        agent_id="test",
    )

    response = client.get("/memory/decision", params={"layer": "L3_project", "scope_id": "proj-1"})

    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "decision"
    assert data["value"] == "ship"
    assert data["scope"]["scope_id"] == "proj-1"


def test_list_memory_filters_by_layer_and_scope() -> None:
    repo = MemoryRepository()
    repo.write(
        MemoryScope(layer=MemoryLayer.PROJECT, scope_id="proj-1"),
        key="visible",
        value="yes",
        tags=None,
        ttl=None,
        agent_id="test",
    )
    repo.write(
        MemoryScope(layer=MemoryLayer.PROJECT, scope_id="proj-2"),
        key="hidden",
        value="no",
        tags=None,
        ttl=None,
        agent_id="test",
    )

    response = client.get("/memory", params={"layer": "L3_project", "scope_id": "proj-1"})

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["key"] == "visible"
