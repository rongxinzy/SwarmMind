"""Project memory repository."""

from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import ProjectMemoryDB
from swarmmind.time_utils import utc_now


class ProjectMemoryRepository:
    """Repository for project-scoped shared memory key-value entries."""

    def list_by_project(self, project_id: str) -> list[ProjectMemoryDB]:
        """List memory entries for a project ordered by key."""
        with session_scope() as session:
            results = session.exec(
                select(ProjectMemoryDB)
                .where(ProjectMemoryDB.project_id == project_id)
                .order_by(ProjectMemoryDB.key.asc()),
            ).all()
            for r in results:
                session.expunge(r)
            return list(results)

    def get(self, project_id: str, key: str) -> ProjectMemoryDB:
        """Get a memory entry or raise 404."""
        with session_scope() as session:
            entry = session.get(ProjectMemoryDB, (project_id, key))
            if entry is None:
                raise HTTPException(status_code=404, detail="Memory entry not found")
            session.expunge(entry)
            return entry

    def set(self, project_id: str, key: str, value: str) -> ProjectMemoryDB:
        """Set a memory entry, creating or updating it."""
        with session_scope() as session:
            entry = session.get(ProjectMemoryDB, (project_id, key))
            if entry is None:
                entry = ProjectMemoryDB(project_id=project_id, key=key, value=value)
                session.add(entry)
            else:
                entry.value = value
                entry.updated_at = utc_now()
            session.commit()
            session.refresh(entry)
            session.expunge(entry)
            return entry

    def delete(self, project_id: str, key: str) -> None:
        """Delete a memory entry if it exists."""
        with session_scope() as session:
            entry = session.get(ProjectMemoryDB, (project_id, key))
            if entry is not None:
                session.delete(entry)
