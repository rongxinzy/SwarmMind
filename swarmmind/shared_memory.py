"""Shared memory layer backed by the configured SwarmMind control-plane database."""

import logging
import time

from swarmmind.config import MEMORY_MAX_RETRIES, MEMORY_RETRY_DELAY_MS
from swarmmind.db import session_scope
from swarmmind.db_models import WorkingMemoryDB

logger = logging.getLogger(__name__)


class SharedMemoryConflict(Exception):
    """Raised when a write conflict cannot be resolved after max retries."""

    pass


class SharedMemory:
    """Key-value store backed by the configured ORM database.

    Phase 1 protocol (last-write-wins):
    1. Read current value + updated_at
    2. Write new value with last_writer_agent_id + updated_at
    3. If conflict (409-like): retry up to MAX_RETRIES with 100ms backoff
    """

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id

    def read(self, key: str) -> dict | None:
        """Read a key from working memory. Returns None if not found."""
        with session_scope() as session:
            entry = session.get(WorkingMemoryDB, key)
            if entry is None:
                return None
            return {
                "key": entry.key,
                "value": entry.value,
                "domain_tags": entry.domain_tags,
                "last_writer_agent_id": entry.last_writer_agent_id,
                "updated_at": entry.updated_at,
            }

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
            with session_scope() as session:
                entry = session.get(WorkingMemoryDB, key)
                prior_updated_at = entry.updated_at if entry else None
                prior_writer = entry.last_writer_agent_id if entry else None

                if entry is None:
                    entry = WorkingMemoryDB(
                        key=key,
                        value=value,
                        domain_tags=domain_tags,
                        last_writer_agent_id=self.agent_id,
                    )
                    session.add(entry)
                else:
                    entry.value = value
                    entry.domain_tags = domain_tags or entry.domain_tags
                    entry.last_writer_agent_id = self.agent_id

                session.commit()

                # Verify: re-read to detect concurrent modification
                session.refresh(entry)
                if prior_updated_at is not None and entry.updated_at != prior_updated_at:
                    logger.debug(
                        "SharedMemory conflict on key=%s (attempt %d/%d). prior_writer=%s, our_writer=%s",
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

        # Should not reach here, but safety net
        raise SharedMemoryConflict(f"Key {key}: max retries exhausted.")

    def read_all_by_tag(self, domain_tag: str) -> list[dict]:
        """Read all entries matching a domain tag."""
        with session_scope() as session:
            from sqlmodel import select

            results = session.exec(
                select(WorkingMemoryDB).where(
                    WorkingMemoryDB.domain_tags.contains(domain_tag),
                ),
            ).all()
            return [
                {
                    "key": r.key,
                    "value": r.value,
                    "domain_tags": r.domain_tags,
                    "last_writer_agent_id": r.last_writer_agent_id,
                    "updated_at": r.updated_at,
                }
                for r in results
            ]

    def read_all(self) -> list[dict]:
        """Read all entries in working memory."""
        with session_scope() as session:
            from sqlmodel import select

            results = session.exec(
                select(WorkingMemoryDB).order_by(WorkingMemoryDB.updated_at.desc()),
            ).all()
            return [
                {
                    "key": r.key,
                    "value": r.value,
                    "domain_tags": r.domain_tags,
                    "last_writer_agent_id": r.last_writer_agent_id,
                    "updated_at": r.updated_at,
                }
                for r in results
            ]
