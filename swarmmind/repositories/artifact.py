"""Artifact repository."""

from __future__ import annotations

import uuid
from typing import Any, cast

from fastapi import HTTPException
from sqlalchemy import or_
from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import ArtifactDB
from swarmmind.services.artifact_content import is_virtual_user_data_path, normalize_virtual_path


class ArtifactRepository:
    """Repository for artifact metadata operations."""

    def create(  # noqa: PLR0913
        self,
        conversation_id: str | None = None,
        message_id: str | None = None,
        name: str | None = None,
        artifact_type: str | None = None,
        project_id: str | None = None,
        run_id: str | None = None,
        task_id: str | None = None,
        author_role: str | None = None,
        path: str | None = None,
        storage_uri: str | None = None,
        mime_type: str | None = None,
        size_bytes: int | None = None,
    ) -> ArtifactDB:
        """Create a new artifact record."""
        normalized_path = normalize_virtual_path(path)
        if normalized_path is not None and not is_virtual_user_data_path(normalized_path):
            normalized_path = None
        if normalized_path is None and is_virtual_user_data_path(name):
            normalized_path = normalize_virtual_path(name)

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
                path=normalized_path,
                storage_uri=storage_uri,
                mime_type=mime_type,
                size_bytes=size_bytes,
                artifact_type=artifact_type,
            )
            session.add(artifact)
            session.commit()
            session.refresh(artifact)
            session.expunge(artifact)
            return artifact

    def get_by_conversation_path(self, conversation_id: str, path: str) -> ArtifactDB:
        """Get a registered artifact for a conversation by virtual path."""
        normalized_path = normalize_virtual_path(path)
        if normalized_path is None:
            raise HTTPException(status_code=404, detail="Artifact not found")

        path_variants = {normalized_path, normalized_path.lstrip("/")}
        path_column = cast(Any, ArtifactDB.path)
        name_column = cast(Any, ArtifactDB.name)
        storage_uri_column = cast(Any, ArtifactDB.storage_uri)
        with session_scope() as session:
            artifact = session.exec(
                select(ArtifactDB)
                .where(ArtifactDB.conversation_id == conversation_id)
                .where(
                    or_(
                        path_column.in_(path_variants),
                        name_column.in_(path_variants),
                        storage_uri_column.in_(path_variants),
                    )
                )
            ).first()
            if artifact is None:
                raise HTTPException(status_code=404, detail="Artifact not found")
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
        created_at_column = cast(Any, ArtifactDB.created_at)
        with session_scope() as session:
            results = session.exec(
                select(ArtifactDB)
                .where(ArtifactDB.conversation_id == conversation_id)
                .order_by(created_at_column.desc()),
            ).all()
            for r in results:
                session.expunge(r)
            return list(results)

    def list_by_project(self, project_id: str) -> list[ArtifactDB]:
        """List artifacts for a project ordered by created_at descending."""
        created_at_column = cast(Any, ArtifactDB.created_at)
        with session_scope() as session:
            results = session.exec(
                select(ArtifactDB).where(ArtifactDB.project_id == project_id).order_by(created_at_column.desc()),
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
