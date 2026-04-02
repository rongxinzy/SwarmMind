"""Runtime model catalog backed by SQLite with env bootstrap for MVP."""

from __future__ import annotations

import os

from swarmmind.config import LLM_BASE_URL, LLM_MODEL, LLM_PROVIDER
from swarmmind.db import get_connection
from swarmmind.runtime.errors import RuntimeConfigError
from swarmmind.runtime.models import RuntimeModel, RuntimeSelectableModel

ANONYMOUS_SUBJECT_TYPE = "visitor_group"
ANONYMOUS_SUBJECT_ID = "anonymous"
ENV_MODEL_SOURCE = "env"


def _provider_defaults(provider: str) -> tuple[str, str]:
    normalized_provider = provider.strip().lower() or "openai"
    if normalized_provider == "anthropic":
        return "langchain_anthropic:ChatAnthropic", "ANTHROPIC_API_KEY"
    return "langchain_openai:ChatOpenAI", "OPENAI_API_KEY"


def _display_name_for_model(model_name: str) -> str:
    return model_name


def infer_env_runtime_model() -> RuntimeModel:
    provider = (os.environ.get("LLM_PROVIDER") or LLM_PROVIDER or "openai").strip().lower()
    model_name = (os.environ.get("LLM_MODEL") or LLM_MODEL or "").strip()
    llm_base_url = os.environ.get("ANTHROPIC_BASE_URL") or os.environ.get("LLM_BASE_URL") or LLM_BASE_URL

    if not model_name:
        raise RuntimeConfigError("LLM_MODEL is required to build the runtime model catalog.")

    model_class, api_key_env_var = _provider_defaults(provider)

    return RuntimeModel(
        name=model_name,
        provider=provider,
        model=model_name,
        display_name=os.environ.get("LLM_DISPLAY_NAME") or _display_name_for_model(model_name),
        description=os.environ.get("LLM_MODEL_DESCRIPTION"),
        model_class=model_class,
        api_key_env_var=api_key_env_var,
        base_url=llm_base_url or None,
        supports_vision=True,
        source=ENV_MODEL_SOURCE,
    )


def sync_env_runtime_model() -> RuntimeModel:
    """Mirror the current env-configured model into the runtime catalog."""
    runtime_model = infer_env_runtime_model()

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE runtime_models SET enabled = 0, updated_at = CURRENT_TIMESTAMP WHERE source = ?",
            (ENV_MODEL_SOURCE,),
        )
        cursor.execute(
            """
            INSERT INTO runtime_models (
                name, provider, model, display_name, description, model_class,
                api_key_env_var, base_url, supports_vision, enabled, source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            ON CONFLICT(name) DO UPDATE SET
                provider = excluded.provider,
                model = excluded.model,
                display_name = excluded.display_name,
                description = excluded.description,
                model_class = excluded.model_class,
                api_key_env_var = excluded.api_key_env_var,
                base_url = excluded.base_url,
                supports_vision = excluded.supports_vision,
                enabled = 1,
                source = excluded.source,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                runtime_model.name,
                runtime_model.provider,
                runtime_model.model,
                runtime_model.display_name,
                runtime_model.description,
                runtime_model.model_class,
                runtime_model.api_key_env_var,
                runtime_model.base_url,
                int(runtime_model.supports_vision),
                runtime_model.source,
            ),
        )
        cursor.execute(
            """
            DELETE FROM runtime_model_assignments
            WHERE subject_type = ? AND subject_id = ?
              AND model_name IN (SELECT name FROM runtime_models WHERE source = ? AND enabled = 0)
            """,
            (ANONYMOUS_SUBJECT_TYPE, ANONYMOUS_SUBJECT_ID, ENV_MODEL_SOURCE),
        )
        cursor.execute(
            """
            UPDATE runtime_model_assignments
            SET is_default = 0
            WHERE subject_type = ? AND subject_id = ?
            """,
            (ANONYMOUS_SUBJECT_TYPE, ANONYMOUS_SUBJECT_ID),
        )
        cursor.execute(
            """
            INSERT INTO runtime_model_assignments (subject_type, subject_id, model_name, is_default)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(subject_type, subject_id, model_name) DO UPDATE SET
                is_default = 1
            """,
            (ANONYMOUS_SUBJECT_TYPE, ANONYMOUS_SUBJECT_ID, runtime_model.name),
        )
        conn.commit()
    finally:
        conn.close()

    return runtime_model


def _row_to_runtime_model(row) -> RuntimeModel:
    return RuntimeModel(
        name=str(row["name"]),
        provider=str(row["provider"]),
        model=str(row["model"]),
        display_name=str(row["display_name"]) if row["display_name"] is not None else None,
        description=str(row["description"]) if row["description"] is not None else None,
        model_class=str(row["model_class"]),
        api_key_env_var=str(row["api_key_env_var"]),
        base_url=str(row["base_url"]) if row["base_url"] is not None else None,
        supports_vision=bool(row["supports_vision"]),
        source=str(row["source"]),
    )


def _row_to_selectable_runtime_model(row) -> RuntimeSelectableModel:
    return RuntimeSelectableModel(
        name=str(row["name"]),
        provider=str(row["provider"]),
        model=str(row["model"]),
        display_name=str(row["display_name"]) if row["display_name"] is not None else None,
        description=str(row["description"]) if row["description"] is not None else None,
        model_class=str(row["model_class"]),
        api_key_env_var=str(row["api_key_env_var"]),
        base_url=str(row["base_url"]) if row["base_url"] is not None else None,
        supports_vision=bool(row["supports_vision"]),
        source=str(row["source"]),
        is_default=bool(row["is_default"]),
    )


def list_enabled_runtime_models() -> list[RuntimeModel]:
    """Return all enabled models that should be injected into DeerFlow config."""
    sync_env_runtime_model()

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT *
            FROM runtime_models
            WHERE enabled = 1
            ORDER BY created_at ASC, name ASC
            """
        )
        return [_row_to_runtime_model(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def list_models_for_subject(
    subject_type: str = ANONYMOUS_SUBJECT_TYPE,
    subject_id: str = ANONYMOUS_SUBJECT_ID,
) -> list[RuntimeSelectableModel]:
    """Return the models available to the given subject."""
    sync_env_runtime_model()

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                m.*,
                a.is_default
            FROM runtime_model_assignments a
            JOIN runtime_models m ON m.name = a.model_name
            WHERE a.subject_type = ?
              AND a.subject_id = ?
              AND m.enabled = 1
            ORDER BY a.is_default DESC, m.created_at ASC, m.name ASC
            """,
            (subject_type, subject_id),
        )
        return [_row_to_selectable_runtime_model(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def resolve_model_for_subject(
    requested_model_name: str | None,
    subject_type: str = ANONYMOUS_SUBJECT_TYPE,
    subject_id: str = ANONYMOUS_SUBJECT_ID,
) -> RuntimeSelectableModel:
    """Validate a requested model or fall back to the subject default."""
    models = list_models_for_subject(subject_type=subject_type, subject_id=subject_id)
    if not models:
        raise RuntimeConfigError(
            f"No runtime models are assigned to {subject_type}:{subject_id}."
        )

    if requested_model_name:
        for model in models:
            if model.name == requested_model_name:
                return model
        raise RuntimeConfigError(
            f"Model '{requested_model_name}' is not assigned to {subject_type}:{subject_id}."
        )

    for model in models:
        if model.is_default:
            return model

    return models[0]
