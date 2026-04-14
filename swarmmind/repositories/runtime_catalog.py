"""Runtime catalog repository."""

from __future__ import annotations

from sqlmodel import Session, select

from swarmmind.db import session_scope
from swarmmind.db_models import RuntimeModelAssignmentDB, RuntimeModelDB
from swarmmind.runtime.models import RuntimeModel, RuntimeSelectableModel


def _db_to_runtime_model(db_model: RuntimeModelDB) -> RuntimeModel:
    return RuntimeModel(
        name=db_model.name,
        provider=db_model.provider,
        model=db_model.model,
        display_name=db_model.display_name,
        description=db_model.description,
        model_class=db_model.model_class,
        api_key_env_var=db_model.api_key_env_var,
        base_url=db_model.base_url,
        supports_vision=bool(db_model.supports_vision),
        source=db_model.source,
    )


def _db_to_selectable_runtime_model(
    db_model: RuntimeModelDB, is_default: bool,
) -> RuntimeSelectableModel:
    return RuntimeSelectableModel(
        name=db_model.name,
        provider=db_model.provider,
        model=db_model.model,
        display_name=db_model.display_name,
        description=db_model.description,
        model_class=db_model.model_class,
        api_key_env_var=db_model.api_key_env_var,
        base_url=db_model.base_url,
        supports_vision=bool(db_model.supports_vision),
        source=db_model.source,
        is_default=bool(is_default),
    )


class RuntimeCatalogRepository:
    """Repository for runtime model catalog operations."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def _with_session(self):
        """Return session context manager or the existing session."""
        if self._session is not None:
            return _NoOpContextManager(self._session)
        return session_scope()

    def sync_env_model(
        self,
        runtime_model: RuntimeModel,
        anonymous_subject_type: str,
        anonymous_subject_id: str,
        env_source: str,
    ) -> None:
        """Mirror the env-configured model into the runtime catalog."""
        with self._with_session() as session:
            # Disable previous env-sourced models
            prev_models = session.exec(
                select(RuntimeModelDB).where(RuntimeModelDB.source == env_source),
            ).all()
            for m in prev_models:
                m.enabled = 0

            # Upsert current env model
            db_model = session.get(RuntimeModelDB, runtime_model.name)
            if db_model is None:
                db_model = RuntimeModelDB(
                    name=runtime_model.name,
                    provider=runtime_model.provider,
                    model=runtime_model.model,
                    display_name=runtime_model.display_name,
                    description=runtime_model.description,
                    model_class=runtime_model.model_class,
                    api_key_env_var=runtime_model.api_key_env_var,
                    base_url=runtime_model.base_url,
                    supports_vision=int(runtime_model.supports_vision),
                    enabled=1,
                    source=runtime_model.source,
                )
                session.add(db_model)
            else:
                db_model.provider = runtime_model.provider
                db_model.model = runtime_model.model
                db_model.display_name = runtime_model.display_name
                db_model.description = runtime_model.description
                db_model.model_class = runtime_model.model_class
                db_model.api_key_env_var = runtime_model.api_key_env_var
                db_model.base_url = runtime_model.base_url
                db_model.supports_vision = int(runtime_model.supports_vision)
                db_model.enabled = 1
                db_model.source = runtime_model.source

            # Remove stale assignments for disabled env models
            disabled_names = {
                m.name for m in prev_models if m.name != runtime_model.name
            }
            if disabled_names:
                stale = session.exec(
                    select(RuntimeModelAssignmentDB).where(
                        RuntimeModelAssignmentDB.subject_type == anonymous_subject_type,
                        RuntimeModelAssignmentDB.subject_id == anonymous_subject_id,
                        RuntimeModelAssignmentDB.model_name.in_(disabled_names),
                    ),
                ).all()
                for a in stale:
                    session.delete(a)

            # Reset defaults for anonymous subject
            existing_assignments = session.exec(
                select(RuntimeModelAssignmentDB).where(
                    RuntimeModelAssignmentDB.subject_type == anonymous_subject_type,
                    RuntimeModelAssignmentDB.subject_id == anonymous_subject_id,
                ),
            ).all()
            for a in existing_assignments:
                a.is_default = 0

            # Set current model as default
            assignment = session.get(
                RuntimeModelAssignmentDB,
                (anonymous_subject_type, anonymous_subject_id, runtime_model.name),
            )
            if assignment is None:
                assignment = RuntimeModelAssignmentDB(
                    subject_type=anonymous_subject_type,
                    subject_id=anonymous_subject_id,
                    model_name=runtime_model.name,
                    is_default=1,
                )
                session.add(assignment)
            else:
                assignment.is_default = 1

            session.commit()

    def list_enabled_models(self) -> list[RuntimeModel]:
        """Return all enabled runtime models."""
        with self._with_session() as session:
            results = session.exec(
                select(RuntimeModelDB)
                .where(RuntimeModelDB.enabled == 1)
                .order_by(RuntimeModelDB.created_at.asc(), RuntimeModelDB.name.asc()),
            ).all()
            return [_db_to_runtime_model(r) for r in results]

    def list_models_for_subject(
        self, subject_type: str, subject_id: str,
    ) -> list[RuntimeSelectableModel]:
        """Return models assigned to the given subject."""
        with self._with_session() as session:
            # Use explicit join via WHERE clauses since SQLite + SQLModel
            # handles this cleanly.
            results = session.exec(
                select(RuntimeModelDB, RuntimeModelAssignmentDB.is_default)
                .join(
                    RuntimeModelAssignmentDB,
                    RuntimeModelDB.name == RuntimeModelAssignmentDB.model_name,
                )
                .where(
                    RuntimeModelAssignmentDB.subject_type == subject_type,
                    RuntimeModelAssignmentDB.subject_id == subject_id,
                    RuntimeModelDB.enabled == 1,
                )
                .order_by(
                    RuntimeModelAssignmentDB.is_default.desc(),
                    RuntimeModelDB.created_at.asc(),
                    RuntimeModelDB.name.asc(),
                ),
            ).all()
            return [
                _db_to_selectable_runtime_model(row[0], row[1])
                for row in results
            ]


class _NoOpContextManager:
    """Wrap an existing session so it can be used in a with statement."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def __enter__(self) -> Session:
        return self._session

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass
