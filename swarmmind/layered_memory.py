"""Layered memory — 4-layer scoped KV store with TTL, CAS, and session promotion."""

import json
import logging
import time
from datetime import datetime

from swarmmind.config import (
    MEMORY_DEFAULT_L1_TTL_SECONDS,
    MEMORY_MAX_RETRIES,
    MEMORY_MAX_TTL_SECONDS,
    MEMORY_RETRY_DELAY_MS,
    SOUL_WRITER_AGENT_IDS,
)
from swarmmind.models import MemoryContext, MemoryEntry, MemoryLayer, MemoryScope
from swarmmind.repositories.memory import MemoryRepository

logger = logging.getLogger(__name__)


class LayeredMemoryError(Exception):
    """Base exception for layered memory errors."""

    pass


class MemoryWriteConflict(LayeredMemoryError):
    """Raised when a CAS write conflict cannot be resolved after max retries."""

    pass


class MemoryWriteForbidden(LayeredMemoryError):
    """Raised when an agent attempts to write to a layer it is not authorized for."""

    pass


class LayeredMemory:
    """4-layer scoped KV store backed by the configured ORM database.

    Layers (L1=L4, L4=USER_SOUL):
      L1 TMP    — session-scoped, TTL support (default 24h)
      L2 TEAM   — team-scoped, no TTL
      L3 PROJECT — project-scoped, no TTL
      L4 USER_SOUL — user-scoped, read-mostly, only soul_writer may write

    Read priority: L1 > L2 > L3 > L4 (first-found wins per key)

    Write protocol (CAS with last-write-wins fallback):
      1. Read current version
      2. Write with version+1 (or INSERT)
      3. On conflict: retry up to MAX_RETRIES
    """

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        self._repo = MemoryRepository()

    # ---- internal helpers ----

    @staticmethod
    def _entry_to_model(db_entry) -> MemoryEntry:
        tags = []
        if db_entry.tags:
            try:
                tags = json.loads(db_entry.tags)
            except json.JSONDecodeError:
                pass
        return MemoryEntry(
            id=db_entry.id,
            scope=MemoryScope(
                layer=MemoryLayer(db_entry.layer),
                scope_id=db_entry.scope_id,
            ),
            key=db_entry.key,
            value=db_entry.value,
            tags=tags,
            created_at=db_entry.created_at,
            updated_at=db_entry.updated_at,
            ttl=db_entry.ttl,
            version=db_entry.version,
            last_writer_agent_id=db_entry.last_writer_agent_id,
        )

    def _is_expired(self, db_entry) -> bool:
        """Check if a memory entry has expired based on its TTL."""
        if db_entry.ttl is None:
            return False
        created = (
            datetime.fromisoformat(db_entry.created_at) if isinstance(db_entry.created_at, str) else db_entry.created_at
        )
        age = (datetime.now() - created).total_seconds()
        return age > db_entry.ttl

    # ---- read ----

    def read(self, key: str, ctx: MemoryContext) -> MemoryEntry | None:
        """Priority-ordered lookup across ctx.visible_scopes.
        Returns the first non-expired entry found.
        Returns None if not found in any layer.
        """
        for scope in ctx.visible_scopes:
            db_entry = self._repo.read(scope, key)
            if db_entry and not self._is_expired(db_entry):
                return self._entry_to_model(db_entry)
        return None

    def read_all(
        self,
        tags: list[str] | None = None,
        layers: list[MemoryLayer] | None = None,
        ctx: MemoryContext | None = None,
    ) -> list[MemoryEntry]:
        """Read all entries matching tag filter across specified layers.

        If ctx is provided, restricts to ctx.visible_scopes.
        If layers is provided, restricts to those layers (takes precedence over ctx).
        """
        if layers:
            layer_filter = [l.value for l in layers]
        elif ctx:
            layer_filter = [s.layer.value for s in ctx.visible_scopes]
        else:
            layer_filter = [l.value for l in MemoryLayer]

        if (layers and ctx) or ctx:
            visible_layer_values = {s.layer.value for s in ctx.visible_scopes}
        elif layers:
            visible_layer_values = set(layer_filter)
        else:
            visible_layer_values = {l.value for l in MemoryLayer}

        db_entries = self._repo.read_all(layer_filter, tags)
        entries = []
        for db_entry in db_entries:
            if self._is_expired(db_entry):
                continue
            if db_entry.layer not in visible_layer_values:
                continue
            entries.append(self._entry_to_model(db_entry))
        return entries

    # ---- write ----

    def write(
        self,
        scope: MemoryScope,
        key: str,
        value: str,
        tags: list[str] | None = None,
        ttl: int | None = None,
        expected_version: int | None = None,
    ) -> MemoryEntry:
        """Write to layered memory with CAS support.

        - L4 (USER_SOUL) writes are restricted to SOUL_WRITER_AGENT_IDS.
        - L1 (TMP) TTL defaults to MEMORY_DEFAULT_L1_TTL_SECONDS if not set.
        - If expected_version is provided, uses CAS (fails if version mismatch).
        - Otherwise: last-write-wins with retry loop.
        """
        # L4 authorization check
        if scope.layer == MemoryLayer.USER_SOUL and self.agent_id not in SOUL_WRITER_AGENT_IDS:
            raise MemoryWriteForbidden(
                f"Agent {self.agent_id} is not authorized to write to L4 USER_SOUL. "
                f"Authorized agents: {SOUL_WRITER_AGENT_IDS}"
            )

        # L1 TTL defaults
        if scope.layer == MemoryLayer.TMP and ttl is None:
            ttl = MEMORY_DEFAULT_L1_TTL_SECONDS

        # Clamp TTL
        if ttl is not None:
            ttl = min(ttl, MEMORY_MAX_TTL_SECONDS)

        for attempt in range(MEMORY_MAX_RETRIES):
            try:
                db_entry = self._repo.write(
                    scope=scope,
                    key=key,
                    value=value,
                    tags=tags,
                    ttl=ttl,
                    agent_id=self.agent_id,
                    expected_version=expected_version,
                )
                return self._entry_to_model(db_entry)
            except MemoryWriteConflict:
                if attempt < MEMORY_MAX_RETRIES - 1:
                    time.sleep(MEMORY_RETRY_DELAY_MS / 1000.0)
                    continue
                raise

        raise MemoryWriteConflict(f"Key {key}: max retries exhausted.")

    # ---- session promotion ----

    def promote_session(
        self,
        session_id: str,
        target: MemoryScope,
        key_filter: list[str] | None = None,
    ) -> str:
        """Migrate L1 (TMP) entries from session_id to target layer."""
        promotion_id = self._repo.promote_session(session_id, target, key_filter)
        logger.info(
            "Promoted session %s -> %s/%s: promotion_id=%s",
            session_id,
            target.layer.value,
            target.scope_id,
            promotion_id,
        )
        return promotion_id

    # ---- compaction hints ----

    def register_compaction(
        self,
        scope: MemoryScope,
        policy: str,
        trigger_count: int = 100,
    ) -> str:
        """Register a compaction hint in the hints table."""
        hint_id = self._repo.register_compaction(scope, policy, trigger_count)
        logger.info(
            "Registered compaction hint: id=%s scope=%s/%s policy=%s trigger=%d",
            hint_id,
            scope.layer.value,
            scope.scope_id,
            policy,
            trigger_count,
        )
        return hint_id
