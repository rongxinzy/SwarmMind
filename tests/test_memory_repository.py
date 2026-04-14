"""Tests for dialect-agnostic memory repository behavior."""

from __future__ import annotations

from datetime import timedelta

import pytest

from swarmmind.db import get_session, init_db, seed_default_agents
from swarmmind.db_models import MemoryEntryDB
from swarmmind.models import MemoryLayer, MemoryScope
from swarmmind.repositories.memory import MemoryRepository
from swarmmind.time_utils import utc_now


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    init_db()
    seed_default_agents()
    yield


def test_delete_expired_removes_only_elapsed_ttl_entries() -> None:
    repo = MemoryRepository()
    scope = MemoryScope(layer=MemoryLayer.TMP, scope_id="session-1")

    expired = repo.write(
        scope=scope,
        key="expired-key",
        value="expired",
        tags=["temp"],
        ttl=60,
        agent_id="finance",
    )
    fresh = repo.write(
        scope=scope,
        key="fresh-key",
        value="fresh",
        tags=["temp"],
        ttl=600,
        agent_id="finance",
    )

    session = get_session()
    try:
        expired_row = session.get(MemoryEntryDB, expired.id)
        fresh_row = session.get(MemoryEntryDB, fresh.id)
        assert expired_row is not None
        assert fresh_row is not None

        expired_row.created_at = utc_now() - timedelta(seconds=120)
        fresh_row.created_at = utc_now() - timedelta(seconds=30)
        session.commit()
    finally:
        session.close()

    deleted = repo.delete_expired()

    assert deleted == 1

    session = get_session()
    try:
        assert session.get(MemoryEntryDB, expired.id) is None
        assert session.get(MemoryEntryDB, fresh.id) is not None
    finally:
        session.close()
