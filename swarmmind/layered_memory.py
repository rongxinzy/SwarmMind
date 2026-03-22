"""Layered memory — 4-layer scoped KV store with TTL, CAS, and session promotion."""

import json
import logging
import time
import uuid
from datetime import datetime

from swarmmind.config import (
    MEMORY_DEFAULT_L1_TTL_SECONDS,
    MEMORY_MAX_RETRIES,
    MEMORY_MAX_TTL_SECONDS,
    MEMORY_RETRY_DELAY_MS,
    SOUL_WRITER_AGENT_IDS,
)
from swarmmind.db import get_connection
from swarmmind.models import MemoryContext, MemoryEntry, MemoryLayer, MemoryScope

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
    """
    4-layer scoped KV store backed by SQLite.

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

    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    # ---- internal helpers ----

    def _entry_to_model(self, row: dict) -> MemoryEntry:
        tags = []
        tags_val = row.get("tags")
        if tags_val:
            try:
                tags = json.loads(tags_val)
            except json.JSONDecodeError:
                pass
        return MemoryEntry(
            id=row["id"],
            scope=MemoryScope(
                layer=MemoryLayer(row["layer"]),
                scope_id=row["scope_id"],
            ),
            key=row["key"],
            value=row["value"],
            tags=tags,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            ttl=row.get("ttl"),
            version=row.get("version", 1),
            last_writer_agent_id=row.get("last_writer_agent_id"),
        )

    def _is_expired(self, row: dict) -> bool:
        """Check if a memory entry has expired based on its TTL."""
        if row.get("ttl") is None:
            return False
        created = datetime.fromisoformat(row["created_at"]) if isinstance(row["created_at"], str) else row["created_at"]
        age = (datetime.now() - created).total_seconds()
        return age > row["ttl"]

    def _scope_where(self, scope: MemoryScope) -> tuple[str, list]:
        return "layer = ? AND scope_id = ?", [scope.layer.value, scope.scope_id]

    # ---- read ----

    def read(self, key: str, ctx: MemoryContext) -> MemoryEntry | None:
        """
        Priority-ordered lookup across ctx.visible_scopes.
        Returns the first non-expired entry found.
        Returns None if not found in any layer.
        """
        for scope in ctx.visible_scopes:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                where, params = self._scope_where(scope)
                cursor.execute(
                    f"SELECT * FROM memory_entries WHERE {where} AND key = ?",
                    [*params, key],
                )
                row = cursor.fetchone()
                if row and not self._is_expired(dict(row)):
                    return self._entry_to_model(dict(row))
            finally:
                conn.close()
        return None

    def read_all(
        self,
        tags: list[str] | None = None,
        layers: list[MemoryLayer] | None = None,
        ctx: MemoryContext | None = None,
    ) -> list[MemoryEntry]:
        """
        Read all entries matching tag filter across specified layers.

        If ctx is provided, restricts to ctx.visible_scopes.
        If layers is provided, restricts to those layers (takes precedence over ctx).
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            # Determine layers to query
            if layers:
                layer_filter = [l.value for l in layers]
            elif ctx:
                layer_filter = [s.layer.value for s in ctx.visible_scopes]
            else:
                layer_filter = [l.value for l in MemoryLayer]

            # Determine which layers are visible (for access control after fetch)
            if layers and ctx:
                # layers takes precedence, but ctx.visible_scopes still constrains access
                visible_layer_values = {s.layer.value for s in ctx.visible_scopes}
            elif ctx:
                visible_layer_values = {s.layer.value for s in ctx.visible_scopes}
            elif layers:
                visible_layer_values = set(layer_filter)
            else:
                visible_layer_values = {l.value for l in MemoryLayer}

            placeholders = ",".join("?" * len(layer_filter))
            sql = f"SELECT * FROM memory_entries WHERE layer IN ({placeholders})"

            params = list(layer_filter)

            if tags:
                tag_conditions = " OR ".join(["tags LIKE ?" for _ in tags])
                sql += f" AND ({tag_conditions})"
                params.extend([f"%{t}%" for t in tags])

            sql += " ORDER BY created_at DESC"

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            entries = []
            for row in rows:
                row_dict = dict(row)
                if self._is_expired(row_dict):
                    continue
                # Layer access control
                if row_dict["layer"] not in visible_layer_values:
                    continue
                entries.append(self._entry_to_model(row_dict))

            return entries
        finally:
            conn.close()

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
        """
        Write to layered memory with CAS support.

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

        tags_json = json.dumps(tags) if tags else None

        for attempt in range(MEMORY_MAX_RETRIES):
            conn = get_connection()
            try:
                cursor = conn.cursor()

                # Check existing entry
                where, params = self._scope_where(scope)
                cursor.execute(
                    f"SELECT id, version FROM memory_entries WHERE {where} AND key = ?",
                    [*params, key],
                )
                existing = cursor.fetchone()

                if expected_version is not None and existing:
                    if existing["version"] != expected_version:
                        raise MemoryWriteConflict(
                            f"CAS conflict: expected version {expected_version}, "
                            f"found version {existing['version']}"
                        )

                new_version = (existing["version"] + 1) if existing else 1
                entry_id = existing["id"] if existing else str(uuid.uuid4())

                cursor.execute(
                    f"""
                    INSERT INTO memory_entries
                    (id, layer, scope_id, key, value, tags, ttl, version, last_writer_agent_id, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(layer, scope_id, key) DO UPDATE SET
                        value                = excluded.value,
                        tags                 = excluded.tags,
                        ttl                  = excluded.ttl,
                        version              = excluded.version,
                        last_writer_agent_id = excluded.last_writer_agent_id,
                        updated_at           = CURRENT_TIMESTAMP
                    """,
                    (
                        entry_id,
                        scope.layer.value,
                        scope.scope_id,
                        key,
                        value,
                        tags_json,
                        ttl,
                        new_version,
                        self.agent_id,
                    ),
                )
                conn.commit()

                # CAS verification: if we expected a specific version, confirm no concurrent write
                if expected_version is not None and existing:
                    cursor.execute(
                        f"SELECT version FROM memory_entries WHERE {where} AND key = ?",
                        [*params, key],
                    )
                    current = cursor.fetchone()
                    if current and current["version"] != new_version:
                        logger.debug(
                            "LayeredMemory CAS conflict on key=%s (attempt %d/%d).",
                            key, attempt + 1, MEMORY_MAX_RETRIES,
                        )
                        if attempt < MEMORY_MAX_RETRIES - 1:
                            time.sleep(MEMORY_RETRY_DELAY_MS / 1000.0)
                            continue
                        else:
                            raise MemoryWriteConflict(
                                f"CAS conflict on key {key} after {MEMORY_MAX_RETRIES} retries."
                            )

                logger.debug(
                    "LayeredMemory write: layer=%s scope_id=%s key=%s version=%d agent=%s",
                    scope.layer.value, scope.scope_id, key, new_version, self.agent_id,
                )
                return self._build_entry(scope, key, value, tags, ttl, new_version)

            finally:
                conn.close()

        raise MemoryWriteConflict(f"Key {key}: max retries exhausted.")

    def _build_entry(
        self,
        scope: MemoryScope,
        key: str,
        value: str,
        tags: list[str] | None,
        ttl: int | None,
        version: int,
    ) -> MemoryEntry:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            where, params = self._scope_where(scope)
            cursor.execute(
                f"SELECT * FROM memory_entries WHERE {where} AND key = ?",
                [*params, key],
            )
            row = cursor.fetchone()
            return self._entry_to_model(dict(row)) if row else MemoryEntry(
                id=str(uuid.uuid4()),
                scope=scope,
                key=key,
                value=value,
                tags=tags or [],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                ttl=ttl,
                version=version,
                last_writer_agent_id=self.agent_id,
            )
        finally:
            conn.close()

    # ---- session promotion ----

    def promote_session(
        self,
        session_id: str,
        target: MemoryScope,
        key_filter: list[str] | None = None,
    ) -> str:
        """
        Migrate L1 (TMP) entries from session_id to target layer.

        Creates a snapshot record in session_promotions and copies matching
        entries to the target layer. Does NOT delete source entries (Phase 2).

        Returns promotion record id.
        """
        promotion_id = str(uuid.uuid4())
        key_filter_json = json.dumps(key_filter) if key_filter else None

        conn = get_connection()
        try:
            cursor = conn.cursor()

            # Find L1 entries for this session
            if key_filter:
                placeholders = ",".join("?" * len(key_filter))
                cursor.execute(
                    f"""
                    SELECT * FROM memory_entries
                    WHERE layer = ? AND scope_id = ? AND key IN ({placeholders})
                    """,
                    [MemoryLayer.TMP.value, session_id] + key_filter,
                )
            else:
                cursor.execute(
                    "SELECT * FROM memory_entries WHERE layer = ? AND scope_id = ?",
                    (MemoryLayer.TMP.value, session_id),
                )
            rows = list(cursor.fetchall())

            migrated = 0
            for row in rows:
                cursor.execute(
                    """
                    INSERT INTO memory_entries
                    (id, layer, scope_id, key, value, tags, ttl, version, last_writer_agent_id, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(layer, scope_id, key) DO UPDATE SET
                        value                = excluded.value,
                        tags                 = excluded.tags,
                        version              = excluded.version + 1,
                        last_writer_agent_id = excluded.last_writer_agent_id,
                        updated_at           = CURRENT_TIMESTAMP
                    """,
                    (
                        str(uuid.uuid4()),
                        target.layer.value,
                        target.scope_id,
                        row["key"],
                        row["value"],
                        row["tags"],
                        None,  # TTL cleared on promotion
                        1,
                        row["last_writer_agent_id"],
                    ),
                )
                migrated += 1

            # Record promotion
            cursor.execute(
                """
                INSERT INTO session_promotions
                (id, session_id, target_layer, target_scope_id, key_filter, snapshot_count)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (promotion_id, session_id, target.layer.value, target.scope_id, key_filter_json, migrated),
            )
            conn.commit()

            logger.info(
                "Promoted session %s -> %s/%s: %d entries migrated (promotion_id=%s)",
                session_id, target.layer.value, target.scope_id, migrated, promotion_id,
            )
            return promotion_id

        finally:
            conn.close()

    # ---- compaction hints ----

    def register_compaction(
        self,
        scope: MemoryScope,
        policy: str,
        trigger_count: int = 100,
    ) -> str:
        """
        Register a compaction hint in the hints table.

        Phase 1: no-op execution (an agent in Phase 2 reads the hints table
        and performs the actual compression).
        """
        hint_id = str(uuid.uuid4())
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO compaction_hints
                (id, scope_layer, scope_id, policy, trigger_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (hint_id, scope.layer.value, scope.scope_id, policy, trigger_count),
            )
            conn.commit()
            logger.info(
                "Registered compaction hint: id=%s scope=%s/%s policy=%s trigger=%d",
                hint_id, scope.layer.value, scope.scope_id, policy, trigger_count,
            )
            return hint_id
        finally:
            conn.close()
