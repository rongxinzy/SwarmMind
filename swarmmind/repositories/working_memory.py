"""Working memory repository."""

from __future__ import annotations

from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import WorkingMemoryDB


class WorkingMemoryRepository:
    """Repository for shared working memory operations."""

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
        domain_tags: str | None,
        agent_id: str,
    ) -> None:
        """Write a key to working memory."""
        with session_scope() as session:
            entry = session.get(WorkingMemoryDB, key)
            if entry is None:
                entry = WorkingMemoryDB(
                    key=key,
                    value=value,
                    domain_tags=domain_tags,
                    last_writer_agent_id=agent_id,
                )
                session.add(entry)
            else:
                entry.value = value
                entry.domain_tags = domain_tags or entry.domain_tags
                entry.last_writer_agent_id = agent_id

    def read_all_by_tag(self, domain_tag: str) -> list[dict]:
        """Read all entries matching a domain tag."""
        with session_scope() as session:
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
