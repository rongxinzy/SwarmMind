"""Run repository."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import RunDB
from swarmmind.time_utils import utc_now


class RunRepository:
    """Repository for run records."""

    def create(
        self,
        *,
        conversation_id: str,
        project_id: str | None = None,
        goal: str | None = None,
        status: str = "running",
    ) -> RunDB:
        """Create a new run record."""
        with session_scope() as session:
            run = RunDB(
                run_id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                project_id=project_id,
                goal=goal,
                status=status,
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            session.expunge(run)
            return run

    def get_by_id(self, run_id: str) -> RunDB:
        """Get a run by ID or raise 404."""
        with session_scope() as session:
            run = session.get(RunDB, run_id)
            if run is None:
                raise HTTPException(status_code=404, detail="Run not found")
            session.expunge(run)
            return run

    def list_by_project(self, project_id: str) -> list[RunDB]:
        """List runs for a project ordered by started_at descending."""
        with session_scope() as session:
            results = session.exec(
                select(RunDB)
                .where(RunDB.project_id == project_id)
                .order_by(RunDB.started_at.desc()),
            ).all()
            for r in results:
                session.expunge(r)
            return list(results)

    def list_by_conversation(self, conversation_id: str) -> list[RunDB]:
        """List runs for a conversation ordered by started_at descending."""
        with session_scope() as session:
            results = session.exec(
                select(RunDB)
                .where(RunDB.conversation_id == conversation_id)
                .order_by(RunDB.started_at.desc()),
            ).all()
            for r in results:
                session.expunge(r)
            return list(results)

    def update_status(
        self,
        run_id: str,
        status: str,
        summary: str | None = None,
    ) -> None:
        """Update run status and optional summary."""
        with session_scope() as session:
            run = session.get(RunDB, run_id)
            if run is None:
                raise HTTPException(status_code=404, detail="Run not found")
            run.status = status
            if summary is not None:
                run.summary = summary
            if status in ("completed", "failed", "blocked"):
                run.completed_at = utc_now()

    def update(
        self,
        run_id: str,
        *,
        project_id: str | None = None,
        status: str | None = None,
        goal: str | None = None,
        summary: str | None = None,
    ) -> RunDB:
        """Update run fields. Only provided fields are changed."""
        with session_scope() as session:
            run = session.get(RunDB, run_id)
            if run is None:
                raise HTTPException(status_code=404, detail="Run not found")
            if project_id is not None:
                run.project_id = project_id
            if status is not None:
                run.status = status
                if status in ("completed", "failed", "blocked"):
                    run.completed_at = utc_now()
            if goal is not None:
                run.goal = goal
            if summary is not None:
                run.summary = summary
            session.commit()
            session.refresh(run)
            session.expunge(run)
            return run

    def link_project(self, run_id: str, project_id: str) -> None:
        """Associate a run with a project."""
        with session_scope() as session:
            run = session.get(RunDB, run_id)
            if run is None:
                raise HTTPException(status_code=404, detail="Run not found")
            run.project_id = project_id
