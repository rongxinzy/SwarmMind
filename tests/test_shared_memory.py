"""Tests for SharedMemory KV store."""

import pytest

from swarmmind.db import init_db, seed_default_agents
from swarmmind.shared_memory import SharedMemory


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    init_db()
    seed_default_agents()
    yield


class TestSharedMemory:
    def test_write_and_read(self):
        sm = SharedMemory("finance")
        sm.write("test_key", "test_value", domain_tags="finance,q3")
        result = sm.read("test_key")
        assert result is not None
        assert result["value"] == "test_value"
        assert result["last_writer_agent_id"] == "finance"
        assert "q3" in result["domain_tags"]

    def test_read_nonexistent_key(self):
        sm = SharedMemory("finance")
        result = sm.read("does_not_exist")
        assert result is None

    def test_read_all_by_tag(self):
        sm1 = SharedMemory("finance")
        sm1.write("key1", "value1", domain_tags="finance")
        sm1.write("key2", "value2", domain_tags="revenue")

        sm2 = SharedMemory("code_review")
        results = sm2.read_all_by_tag("finance")
        assert len(results) >= 1
        assert any(r["key"] == "key1" for r in results)

    def test_overwrite_existing_key(self):
        sm = SharedMemory("finance")
        sm.write("key1", "value1", domain_tags="finance")
        sm.write("key1", "value2", domain_tags="finance,q3")
        result = sm.read("key1")
        assert result["value"] == "value2"

    def test_read_all(self):
        sm = SharedMemory("finance")
        sm.write("k1", "v1", domain_tags="finance")
        sm.write("k2", "v2", domain_tags="revenue")
        results = sm.read_all()
        keys = {r["key"] for r in results}
        assert "k1" in keys
        assert "k2" in keys
