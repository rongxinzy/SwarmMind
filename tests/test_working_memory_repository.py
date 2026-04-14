"""Tests for WorkingMemoryRepository compatibility behavior."""

import pytest

from swarmmind.db import init_db, seed_default_agents
from swarmmind.repositories.working_memory import WorkingMemoryRepository


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    init_db()
    seed_default_agents()
    yield


class TestWorkingMemoryRepository:
    def test_write_and_read_match_shared_memory_semantics(self):
        repo = WorkingMemoryRepository()

        repo.write("test_key", "test_value", "finance,q3", "finance")
        result = repo.read("test_key")

        assert result is not None
        assert result["value"] == "test_value"
        assert result["last_writer_agent_id"] == "finance"
        assert "q3" in result["domain_tags"]

    def test_write_preserves_existing_tags_when_domain_tags_is_none(self):
        repo = WorkingMemoryRepository()

        repo.write("tagged_key", "value1", "finance,q3", "finance")
        repo.write("tagged_key", "value2", None, "code_review")
        result = repo.read("tagged_key")

        assert result is not None
        assert result["value"] == "value2"
        assert result["domain_tags"] == "finance,q3"
        assert result["last_writer_agent_id"] == "code_review"

    def test_read_all_by_tag_and_read_all_delegate_consistently(self):
        repo = WorkingMemoryRepository()

        repo.write("finance_key", "value1", "finance", "finance")
        repo.write("revenue_key", "value2", "revenue", "finance")

        finance_results = repo.read_all_by_tag("finance")
        all_results = repo.read_all()

        assert any(item["key"] == "finance_key" for item in finance_results)
        assert {item["key"] for item in all_results} >= {"finance_key", "revenue_key"}
