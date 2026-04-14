"""Layered memory repository."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import CompactionHintDB, MemoryEntryDB, SessionPromotionDB
from swarmmind.models import MemoryEntry, MemoryLayer, MemoryScope


class MemoryRepository:
    """Repository for layered memory operations."""

    def read(self, scope: MemoryScope, key: str) -> MemoryEntryDB | None:
        """Read a single memory entry by scope and key."""
        with session_scope() as session:
            entry = session.exec(
                select(MemoryEntryDB).where(
                    MemoryEntryDB.layer == scope.layer.value,
                    MemoryEntryDB.scope_id == scope.scope_id,
                    MemoryEntryDB.key == key,
                ),
            ).first()
            if entry is None:
                return None
            session.refresh(entry)
            # Detach so it can be used outside the session
            session.expunge(entry)
            return entry

    def read_all(
        self,
        layers: list[str],
        tags: list[str] | None = None,
    ) -> list[MemoryEntryDB]:
        """Read all entries matching layer filter and optional tags."""
        with session_scope() as session:
            query = select(MemoryEntryDB).where(MemoryEntryDB.layer.in_(layers))
            if tags:
                # Simple LIKE match for each tag (same semantics as original)
                for tag in tags:
                    query = query.where(MemoryEntryDB.tags.contains(tag))
            query = query.order_by(MemoryEntryDB.created_at.desc())
            results = session.exec(query).all()
            for r in results:
                session.expunge(r)
            return list(results)

    def write(
        self,
        scope: MemoryScope,
        key: str,
        value: str,
        tags: list[str] | None,
        ttl: int | None,
        agent_id: str,
        expected_version: int | None = None,
    ) -> MemoryEntryDB:
        """Write to layered memory with optional CAS."""
        with session_scope() as session:
            entry = session.exec(
                select(MemoryEntryDB).where(
                    MemoryEntryDB.layer == scope.layer.value,
                    MemoryEntryDB.scope_id == scope.scope_id,
                    MemoryEntryDB.key == key,
                ),
            ).first()

            if expected_version is not None and entry:
                if entry.version != expected_version:
                    from swarmmind.layered_memory import MemoryWriteConflict
                    raise MemoryWriteConflict(
                        f"CAS conflict: expected version {expected_version}, found version {entry.version}"
                    )

            new_version = (entry.version + 1) if entry else 1
            entry_id = entry.id if entry else str(uuid.uuid4())

            if entry is None:
                entry = MemoryEntryDB(
                    id=entry_id,
                    layer=scope.layer.value,
                    scope_id=scope.scope_id,
                    key=key,
                    value=value,
                    tags=json.dumps(tags) if tags else None,
                    ttl=ttl,
                    version=new_version,
                    last_writer_agent_id=agent_id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                session.add(entry)
            else:
                entry.value = value
                entry.tags = json.dumps(tags) if tags else None
                entry.ttl = ttl
                entry.version = new_version
                entry.last_writer_agent_id = agent_id
                entry.updated_at = datetime.utcnow()

            session.commit()
            session.refresh(entry)
            session.expunge(entry)
            return entry

    def promote_session(
        self,
        session_id: str,
        target: MemoryScope,
        key_filter: list[str] | None,
    ) -> str:
        """Migrate L1 (TMP) entries from session_id to target layer."""
        promotion_id = str(uuid.uuid4())
        key_filter_json = json.dumps(key_filter) if key_filter else None

        with session_scope() as session:
            query = select(MemoryEntryDB).where(
                MemoryEntryDB.layer == MemoryLayer.TMP.value,
                MemoryEntryDB.scope_id == session_id,
            )
            if key_filter:
                query = query.where(MemoryEntryDB.key.in_(key_filter))

            rows = session.exec(query).all()
            migrated = 0
            for row in rows:
                entry = session.exec(
                    select(MemoryEntryDB).where(
                        MemoryEntryDB.layer == target.layer.value,
                        MemoryEntryDB.scope_id == target.scope_id,
                        MemoryEntryDB.key == row.key,
                    ),
                ).first()
                if entry is None:
                    entry = MemoryEntryDB(
                        id=str(uuid.uuid4()),
                        layer=target.layer.value,
                        scope_id=target.scope_id,
                        key=row.key,
                        value=row.value,
                        tags=row.tags,
                        ttl=None,
                        version=1,
                        last_writer_agent_id=row.last_writer_agent_id,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    session.add(entry)
                else:
                    entry.value = row.value
                    entry.tags = row.tags
                    entry.version += 1
                    entry.last_writer_agent_id = row.last_writer_agent_id
                    entry.updated_at = datetime.utcnow()
                migrated += 1

            promo = SessionPromotionDB(
                id=promotion_id,
                session_id=session_id,
                target_layer=target.layer.value,
                target_scope_id=target.scope_id,
                key_filter=key_filter_json,
                snapshot_count=migrated,
            )
            session.add(promo)
            session.commit()
            return promotion_id

    def register_compaction(
        self,
        scope: MemoryScope,
        policy: str,
        trigger_count: int,
    ) -> str:
        """Register a compaction hint."""
        hint_id = str(uuid.uuid4())
        with session_scope() as session:
            hint = CompactionHintDB(
                id=hint_id,
                scope_layer=scope.layer.value,
                scope_id=scope.scope_id,
                policy=policy,
                trigger_count=trigger_count,
            )
            session.add(hint)
            session.commit()
            return hint_id

    def delete_expired(self) -> int:
        """Delete memory entries whose TTL has elapsed. Returns delete count."""
        from sqlalchemy import func

        with session_scope() as session:
            # SQLite-compatible: strftime('%s', 'now') - strftime('%s', created_at) > ttl
            results = session.exec(
                select(MemoryEntryDB).where(
                    MemoryEntryDB.ttl.is_not(None),
                    (
                        func.strftime("%s", "now") - func.strftime("%s", MemoryEntryDB.created_at)
                    )
                    > MemoryEntryDB.ttl,
                ),
            ).all()
            count = 0
            for row in results:
                session.delete(row)
                count += 1
            return count
