"""Tests for LayeredMemory KV store."""

import pytest

from swarmmind.db import init_db, seed_default_agents
from swarmmind.layered_memory import (
    LayeredMemory,
    MemoryWriteConflict,
    MemoryWriteForbidden,
)
from swarmmind.models import MemoryContext, MemoryLayer, MemoryScope


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    """Use a temporary DB for each test."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("SWARMMIND_DB_PATH", db_path)
    init_db()
    seed_default_agents()
    yield


class TestLayeredMemoryWriteRead:
    """Basic write/read tests."""

    def test_write_and_read_l1(self):
        lm = LayeredMemory("finance")
        scope = MemoryScope(layer=MemoryLayer.TMP, scope_id="session-abc")
        entry = lm.write(scope, "key1", "value1", tags=["finance"])

        assert entry.key == "key1"
        assert entry.value == "value1"
        assert entry.scope.layer == MemoryLayer.TMP
        assert entry.scope.scope_id == "session-abc"
        assert "finance" in entry.tags
        assert entry.ttl is not None  # L1 gets auto-TTL

    def test_write_and_read_l2(self):
        lm = LayeredMemory("finance")
        scope = MemoryScope(layer=MemoryLayer.TEAM, scope_id="team-xyz")
        entry = lm.write(scope, "key1", "value1", tags=["revenue"])

        assert entry.key == "key1"
        assert entry.scope.layer == MemoryLayer.TEAM

        ctx = MemoryContext(user_id="u1", team_id="team-xyz")
        result = lm.read("key1", ctx)
        assert result is not None
        assert result.value == "value1"

    def test_write_and_read_l3(self):
        lm = LayeredMemory("finance")
        scope = MemoryScope(layer=MemoryLayer.PROJECT, scope_id="proj-123")
        lm.write(scope, "budget", "100k", tags=["budget"])

        ctx = MemoryContext(user_id="u1", project_id="proj-123")
        result = lm.read("budget", ctx)
        assert result is not None
        assert result.value == "100k"

    def test_read_nonexistent_key(self):
        lm = LayeredMemory("finance")
        ctx = MemoryContext(user_id="u1", session_id="session-abc")
        result = lm.read("does_not_exist", ctx)
        assert result is None


class TestPriorityRead:
    """L1 > L2 > L3 > L4 priority resolution."""

    def test_l1_overrides_l3(self):
        lm = LayeredMemory("finance")

        l1_scope = MemoryScope(layer=MemoryLayer.TMP, scope_id="session-abc")
        l3_scope = MemoryScope(layer=MemoryLayer.PROJECT, scope_id="proj-123")

        lm.write(l3_scope, "key1", "L3-value")
        lm.write(l1_scope, "key1", "L1-value")

        ctx = MemoryContext(
            user_id="u1",
            project_id="proj-123",
            session_id="session-abc",
        )
        result = lm.read("key1", ctx)
        assert result is not None
        assert result.value == "L1-value"
        assert result.scope.layer == MemoryLayer.TMP

    def test_l2_overrides_l4(self):
        lm = LayeredMemory("finance")

        # L4 requires soul_writer; use separate instance for L4 write
        soul_writer = LayeredMemory("soul_writer")
        l4_scope = MemoryScope(layer=MemoryLayer.USER_SOUL, scope_id="u1")
        l2_scope = MemoryScope(layer=MemoryLayer.TEAM, scope_id="team-xyz")

        soul_writer.write(l4_scope, "pref", "L4-pref")
        lm.write(l2_scope, "pref", "L2-pref")

        ctx = MemoryContext(user_id="u1", team_id="team-xyz")
        result = lm.read("pref", ctx)
        assert result.value == "L2-pref"

    def test_l4_fallback_when_no_higher_scope(self):
        soul_writer = LayeredMemory("soul_writer")
        l4_scope = MemoryScope(layer=MemoryLayer.USER_SOUL, scope_id="u1")
        soul_writer.write(l4_scope, "global_setting", "from-L4")

        lm = LayeredMemory("finance")
        ctx = MemoryContext(user_id="u1")  # no session/team/project
        result = lm.read("global_setting", ctx)
        assert result is not None
        assert result.value == "from-L4"


class TestTTLExpiry:
    """TTL-based expiry for L1 entries."""

    def test_l1_auto_ttl(self):
        lm = LayeredMemory("finance")
        scope = MemoryScope(layer=MemoryLayer.TMP, scope_id="session-abc")
        entry = lm.write(scope, "temp_key", "temp_value", tags=["temp"])

        # L1 should have auto-attached TTL
        assert entry.ttl is not None
        assert entry.ttl > 0

    def test_l3_no_auto_ttl(self):
        lm = LayeredMemory("finance")
        scope = MemoryScope(layer=MemoryLayer.PROJECT, scope_id="proj-123")
        entry = lm.write(scope, "proj_key", "proj_value", tags=["proj"])

        # L3 has no auto-TTL
        assert entry.ttl is None

    def test_explicit_ttl_respected(self):
        lm = LayeredMemory("finance")
        scope = MemoryScope(layer=MemoryLayer.TMP, scope_id="session-abc")
        entry = lm.write(scope, "short_ttl", "value", tags=[], ttl=60)

        assert entry.ttl == 60


class TestCASVersionConflict:
    """CAS version checking on write."""

    def test_cas_success(self):
        lm = LayeredMemory("finance")
        scope = MemoryScope(layer=MemoryLayer.TMP, scope_id="session-abc")
        entry = lm.write(scope, "cas_key", "v1", tags=[])

        # Write with correct expected version
        entry2 = lm.write(
            scope,
            "cas_key",
            "v2",
            tags=[],
            expected_version=entry.version,
        )
        assert entry2.value == "v2"
        assert entry2.version == entry.version + 1

    def test_cas_conflict(self):
        lm = LayeredMemory("finance")
        scope = MemoryScope(layer=MemoryLayer.TMP, scope_id="session-abc")
        entry = lm.write(scope, "cas_key", "v1", tags=[])

        # Someone else writes in between
        lm2 = LayeredMemory("code_review")
        lm2.write(scope, "cas_key", "v2", tags=[])

        # Our CAS should fail
        with pytest.raises(MemoryWriteConflict):
            lm.write(
                scope,
                "cas_key",
                "v3",
                tags=[],
                expected_version=entry.version,
            )


class TestL4WriteAuthorization:
    """L4 USER_SOUL is restricted to soul_writer agents."""

    def test_regular_agent_cannot_write_l4(self):
        lm = LayeredMemory("finance")  # not in SOUL_WRITER_AGENT_IDS
        scope = MemoryScope(layer=MemoryLayer.USER_SOUL, scope_id="user-123")

        with pytest.raises(MemoryWriteForbidden):
            lm.write(scope, "soul_key", "soul_value", tags=[])

    def test_soul_writer_can_write_l4(self):
        lm = LayeredMemory("soul_writer")  # in SOUL_WRITER_AGENT_IDS
        scope = MemoryScope(layer=MemoryLayer.USER_SOUL, scope_id="user-123")
        entry = lm.write(scope, "soul_key", "soul_value", tags=["user_trait"])

        assert entry.value == "soul_value"


class TestReadAllWithTags:
    """Tag-filtered batch reads."""

    def test_read_all_filters_by_tags(self):
        lm = LayeredMemory("finance")
        scope = MemoryScope(layer=MemoryLayer.TMP, scope_id="session-abc")

        lm.write(scope, "k1", "v1", tags=["finance", "q3"])
        lm.write(scope, "k2", "v2", tags=["revenue"])
        lm.write(scope, "k3", "v3", tags=["finance"])

        ctx = MemoryContext(user_id="u1", session_id="session-abc")
        results = lm.read_all(tags=["finance"], ctx=ctx)

        keys = {r.key for r in results}
        assert "k1" in keys
        assert "k3" in keys
        assert "k2" not in keys

    def test_read_all_respects_layer_filter(self):
        lm = LayeredMemory("finance")
        l1_scope = MemoryScope(layer=MemoryLayer.TMP, scope_id="session-abc")
        l2_scope = MemoryScope(layer=MemoryLayer.TEAM, scope_id="team-xyz")

        lm.write(l1_scope, "k1", "v1", tags=["tag1"])
        lm.write(l2_scope, "k2", "v2", tags=["tag1"])

        ctx = MemoryContext(user_id="u1", session_id="session-abc", team_id="team-xyz")
        results = lm.read_all(tags=["tag1"], layers=[MemoryLayer.TMP], ctx=ctx)

        keys = {r.key for r in results}
        assert "k1" in keys
        assert "k2" not in keys


class TestSessionPromotion:
    """L1 → L3/L2 migration via promote_session()."""

    def test_promote_session_creates_promotion_record(self):
        lm = LayeredMemory("finance")
        l1_scope = MemoryScope(layer=MemoryLayer.TMP, scope_id="session-abc")
        l3_scope = MemoryScope(layer=MemoryLayer.PROJECT, scope_id="proj-123")

        lm.write(l1_scope, "promote_me", "data", tags=["finance"])

        promotion_id = lm.promote_session("session-abc", l3_scope)

        assert promotion_id is not None

        # Verify promotion record exists
        from swarmmind.db import get_session
        from swarmmind.db_models import SessionPromotionDB

        session = get_session()
        try:
            row = session.get(SessionPromotionDB, promotion_id)
            assert row is not None
            assert row.target_layer == "L3_project"
            assert row.target_scope_id == "proj-123"
        finally:
            session.close()

    def test_promote_session_copies_entries(self):
        lm = LayeredMemory("finance")
        l1_scope = MemoryScope(layer=MemoryLayer.TMP, scope_id="session-abc")
        l3_scope = MemoryScope(layer=MemoryLayer.PROJECT, scope_id="proj-123")

        lm.write(l1_scope, "promote_key", "promoted_data", tags=["finance"])

        lm.promote_session("session-abc", l3_scope)

        # Read from L3
        ctx = MemoryContext(user_id="u1", project_id="proj-123")
        result = lm.read("promote_key", ctx)

        assert result is not None
        assert result.value == "promoted_data"
        assert result.scope.layer == MemoryLayer.PROJECT


class TestCompactionHints:
    """Compaction hint registration (Phase 1: no-op execution)."""

    def test_register_compaction_writes_hint(self):
        lm = LayeredMemory("finance")
        scope = MemoryScope(layer=MemoryLayer.TMP, scope_id="session-abc")

        hint_id = lm.register_compaction(scope, policy="dedup", trigger_count=50)

        assert hint_id is not None

        from swarmmind.db import get_session
        from swarmmind.db_models import CompactionHintDB

        session = get_session()
        try:
            row = session.get(CompactionHintDB, hint_id)
            assert row is not None
            assert row.policy == "dedup"
            assert row.trigger_count == 50
        finally:
            session.close()
