"""Audit log repository."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import AuditLogDB


class AuditLogRepository:
    """Repository for audit log entries."""

    def create(
        self,
        *,
        audit_type: str = "approval_decision",
        project_id: str,
        run_id: str | None = None,
        approval_id: str | None = None,
        actor_id: str | None = None,
        actor_type: str = "user",
        decision: str | None = None,
        reason: str | None = None,
        extra_data: dict | None = None,
    ) -> AuditLogDB:
        """Create a new audit log entry."""
        with session_scope() as session:
            entry = AuditLogDB(
                audit_id=str(uuid.uuid4()),
                audit_type=audit_type,
                project_id=project_id,
                run_id=run_id,
                approval_id=approval_id,
                actor_id=actor_id,
                actor_type=actor_type,
                decision=decision,
                reason=reason,
                extra_data=extra_data,
            )
            session.add(entry)
            session.commit()
            session.refresh(entry)
            session.expunge(entry)
            return entry

    def get(self, audit_id: str) -> AuditLogDB:
        """Get an audit log entry by ID or raise 404."""
        with session_scope() as session:
            entry = session.get(AuditLogDB, audit_id)
            if entry is None:
                raise HTTPException(status_code=404, detail="Audit log entry not found")
            session.expunge(entry)
            return entry

    def list_by_project(self, project_id: str) -> list[AuditLogDB]:
        """List audit log entries for a project ordered by timestamp descending."""
        with session_scope() as session:
            results = session.exec(
                select(AuditLogDB)
                .where(AuditLogDB.project_id == project_id)
                .order_by(AuditLogDB.timestamp.desc()),
            ).all()
            for r in results:
                session.expunge(r)
            return list(results)

    def list_by_run(self, run_id: str) -> list[AuditLogDB]:
        """List audit log entries for a run ordered by timestamp descending."""
        with session_scope() as session:
            results = session.exec(
                select(AuditLogDB)
                .where(AuditLogDB.run_id == run_id)
                .order_by(AuditLogDB.timestamp.desc()),
            ).all()
            for r in results:
                session.expunge(r)
            return list(results)

    def list_by_approval(self, approval_id: str) -> list[AuditLogDB]:
        """List audit log entries for an approval request ordered by timestamp descending."""
        with session_scope() as session:
            results = session.exec(
                select(AuditLogDB)
                .where(AuditLogDB.approval_id == approval_id)
                .order_by(AuditLogDB.timestamp.desc()),
            ).all()
            for r in results:
                session.expunge(r)
            return list(results)

    def list_by_filters(
        self,
        project_id: str | None = None,
        run_id: str | None = None,
        approval_id: str | None = None,
    ) -> list[AuditLogDB]:
        """List audit log entries with optional filters ordered by timestamp descending."""
        with session_scope() as session:
            query = select(AuditLogDB)
            if project_id is not None:
                query = query.where(AuditLogDB.project_id == project_id)
            if run_id is not None:
                query = query.where(AuditLogDB.run_id == run_id)
            if approval_id is not None:
                query = query.where(AuditLogDB.approval_id == approval_id)
            query = query.order_by(AuditLogDB.timestamp.desc())
            results = session.exec(query).all()
            for r in results:
                session.expunge(r)
            return list(results)

    def delete(self, audit_id: str) -> None:
        """Delete an audit log entry by ID."""
        with session_scope() as session:
            entry = session.get(AuditLogDB, audit_id)
            if entry is not None:
                session.delete(entry)
