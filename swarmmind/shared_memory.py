"""Shared memory layer — SQLite-backed KV store with last-write-wins + 409 retry."""

import logging
import time

from swarmmind.config import MEMORY_MAX_RETRIES, MEMORY_RETRY_DELAY_MS
from swarmmind.db import get_connection

logger = logging.getLogger(__name__)


class SharedMemoryConflict(Exception):
    """Raised when a write conflict cannot be resolved after max retries."""

    pass


class SharedMemory:
    """Key-value store backed by SQLite.

    Phase 1 protocol (last-write-wins):
    1. Read current value + updated_at
    2. Write new value with last_writer_agent_id + updated_at
    3. If conflict (409-like): retry up to MAX_RETRIES with 100ms backoff
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    def read(self, key: str) -> dict | None:
        """Read a key from working memory. Returns None if not found."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT key, value, domain_tags, last_writer_agent_id, updated_at "
                "FROM working_memory WHERE key = ?",
                (key,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return {
                "key": row["key"],
                "value": row["value"],
                "domain_tags": row["domain_tags"],
                "last_writer_agent_id": row["last_writer_agent_id"],
                "updated_at": row["updated_at"],
            }
        finally:
            conn.close()

    def write(
        self,
        key: str,
        value: str,
        domain_tags: str | None = None,
    ) -> None:
        """Write a key to working memory. Implements last-write-wins with retry.

        Raises SharedMemoryConflict if all retries are exhausted.
        """
        for attempt in range(MEMORY_MAX_RETRIES):
            conn = get_connection()
            try:
                cursor = conn.cursor()
                # Read current state
                cursor.execute(
                    "SELECT updated_at, last_writer_agent_id FROM working_memory WHERE key = ?",
                    (key,),
                )
                row = cursor.fetchone()
                prior_updated_at = row["updated_at"] if row else None
                prior_writer = row["last_writer_agent_id"] if row else None

                # Write new value
                cursor.execute(
                    """
                    INSERT INTO working_memory (key, value, domain_tags, last_writer_agent_id, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET
                        value       = excluded.value,
                        domain_tags = COALESCE(excluded.domain_tags, domain_tags),
                        last_writer_agent_id = excluded.last_writer_agent_id,
                        updated_at  = CURRENT_TIMESTAMP
                    """,
                    (key, value, domain_tags, self.agent_id),
                )
                conn.commit()

                # Verify: if another agent wrote since our read, retry
                if prior_updated_at is not None:
                    cursor.execute("SELECT updated_at FROM working_memory WHERE key = ?", (key,))
                    current = cursor.fetchone()
                    if current and current["updated_at"] != prior_updated_at:
                        # Another agent wrote in between — conflict, retry
                        logger.debug(
                            "SharedMemory conflict on key=%s (attempt %d/%d). "
                            "prior_writer=%s, our_writer=%s",
                            key,
                            attempt + 1,
                            MEMORY_MAX_RETRIES,
                            prior_writer,
                            self.agent_id,
                        )
                        if attempt < MEMORY_MAX_RETRIES - 1:
                            time.sleep(MEMORY_RETRY_DELAY_MS / 1000.0)
                            continue
                        raise SharedMemoryConflict(
                            f"Key {key} updated by {prior_writer} while we were writing. "
                            f"Max retries ({MEMORY_MAX_RETRIES}) exhausted."
                        )

                logger.debug("SharedMemory write: key=%s by agent=%s", key, self.agent_id)
                return

            finally:
                conn.close()

        # Should not reach here, but safety net
        raise SharedMemoryConflict(f"Key {key}: max retries exhausted.")

    def read_all_by_tag(self, domain_tag: str) -> list[dict]:
        """Read all entries matching a domain tag."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT key, value, domain_tags, last_writer_agent_id, updated_at "
                "FROM working_memory WHERE domain_tags LIKE ?",
                (f"%{domain_tag}%",),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def read_all(self) -> list[dict]:
        """Read all entries in working memory."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT key, value, domain_tags, last_writer_agent_id, updated_at "
                "FROM working_memory ORDER BY updated_at DESC"
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
