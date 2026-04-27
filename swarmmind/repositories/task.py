"""Task repository."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import TaskDB
from swarmmind.time_utils import utc_now


class TaskRepository:
    """Repository for project task operations."""

    def create(
        self,
        *,
        project_id: str,
        run_id: str | None = None,
        title: str,
        description: str | None = None,
        status: str = "todo",
        assignee_role: str | None = None,
        source_workstream: str | None = None,
        artifact_ids: list[str] | None = None,
        priority: str = "medium",
    ) -> TaskDB:
        """Create a new task record."""
        with session_scope() as session:
            task = TaskDB(
                task_id=str(uuid.uuid4()),
                project_id=project_id,
                run_id=run_id,
                title=title,
                description=description,
                status=status,
                assignee_role=assignee_role,
                source_workstream=source_workstream,
                artifact_ids=artifact_ids,
                priority=priority,
            )
            session.add(task)
            session.commit()
            session.refresh(task)
            session.expunge(task)
            return task

    def get_by_id(self, task_id: str) -> TaskDB:
        """Get a task by ID or raise 404."""
        with session_scope() as session:
            task = session.get(TaskDB, task_id)
            if task is None:
                raise HTTPException(status_code=404, detail="Task not found")
            session.expunge(task)
            return task

    def list_by_project(self, project_id: str) -> list[TaskDB]:
        """List tasks for a project ordered by created_at descending."""
        with session_scope() as session:
            results = session.exec(
                select(TaskDB)
                .where(TaskDB.project_id == project_id)
                .order_by(TaskDB.created_at.desc()),
            ).all()
            for r in results:
                session.expunge(r)
            return list(results)

    def update(
        self,
        task_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        assignee_role: str | None = None,
        source_workstream: str | None = None,
        artifact_ids: list[str] | None = None,
        priority: str | None = None,
        run_id: str | None = None,
    ) -> TaskDB:
        """Update task fields. Only provided fields are changed."""
        with session_scope() as session:
            task = session.get(TaskDB, task_id)
            if task is None:
                raise HTTPException(status_code=404, detail="Task not found")
            if title is not None:
                task.title = title
            if description is not None:
                task.description = description
            if status is not None:
                task.status = status
            if assignee_role is not None:
                task.assignee_role = assignee_role
            if source_workstream is not None:
                task.source_workstream = source_workstream
            if artifact_ids is not None:
                task.artifact_ids = artifact_ids
            if priority is not None:
                task.priority = priority
            if run_id is not None:
                task.run_id = run_id
            task.updated_at = utc_now()
            session.commit()
            session.refresh(task)
            session.expunge(task)
            return task

    def delete(self, task_id: str) -> None:
        """Delete a task by ID."""
        with session_scope() as session:
            task = session.get(TaskDB, task_id)
            if task is not None:
                session.delete(task)
