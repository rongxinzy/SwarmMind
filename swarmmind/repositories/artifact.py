"""Artifact repository."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import ArtifactDB


class ArtifactRepository:
    """Repository for artifact metadata operations."""

    def create(
        self,
        conversation_id: str | None = None,
        message_id: str | None = None,
        name: str | None = None,
        artifact_type: str | None = None,
        project_id: str | None = None,
        run_id: str | None = None,
        task_id: str | None = None,
        author_role: str | None = None,
    ) -> ArtifactDB:
        """Create a new artifact record."""
        with session_scope() as session:
            artifact = ArtifactDB(
                artifact_id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                project_id=project_id,
                message_id=message_id,
                run_id=run_id,
                task_id=task_id,
                author_role=author_role,
                name=name,
                artifact_type=artifact_type,
            )
            session.add(artifact)
            session.commit()
            session.refresh(artifact)
            session.expunge(artifact)
            return artifact

    def get_by_id(self, artifact_id: str) -> ArtifactDB:
        """Get an artifact by ID or raise 404."""
        with session_scope() as session:
            artifact = session.get(ArtifactDB, artifact_id)
            if artifact is None:
                raise HTTPException(status_code=404, detail="Artifact not found")
            session.expunge(artifact)
            return artifact

    def list_by_conversation(self, conversation_id: str) -> list[ArtifactDB]:
        """List artifacts for a conversation ordered by created_at descending."""
        with session_scope() as session:
            results = session.exec(
                select(ArtifactDB)
                .where(ArtifactDB.conversation_id == conversation_id)
                .order_by(ArtifactDB.created_at.desc()),
            ).all()
            for r in results:
                session.expunge(r)
            return list(results)

    def list_by_project(self, project_id: str) -> list[ArtifactDB]:
        """List artifacts for a project ordered by created_at descending."""
        with session_scope() as session:
            results = session.exec(
                select(ArtifactDB)
                .where(ArtifactDB.project_id == project_id)
                .order_by(ArtifactDB.created_at.desc()),
            ).all()
            for r in results:
                session.expunge(r)
            return list(results)

    def delete(self, artifact_id: str) -> None:
        """Delete an artifact by ID."""
        with session_scope() as session:
            artifact = session.get(ArtifactDB, artifact_id)
            if artifact is not None:
                session.delete(artifact)
