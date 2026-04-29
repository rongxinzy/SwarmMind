"""Runtime model catalog backed by the configured SwarmMind database.

Design Principle: Zero hardcoded model/provider details.
All model configuration comes from environment variables.
"""

from __future__ import annotations

import os

from sqlmodel import select

from swarmmind.repositories.runtime_catalog import RuntimeCatalogRepository
from swarmmind.runtime.errors import RuntimeConfigError
from swarmmind.runtime.models import RuntimeModel, RuntimeSelectableModel

ANONYMOUS_SUBJECT_TYPE = "visitor_group"
ANONYMOUS_SUBJECT_ID = "anonymous"
ENV_MODEL_SOURCE = "env"


def _infer_model_class(provider: str) -> str:
    """Infer LangChain model class from provider hint.

    This is a convention-based default, NOT hardcoded model details.
    Can be overridden via LLM_MODEL_CLASS env var.
    """
    provider_lower = (provider or "openai").lower()
    # Only distinguish between anthropic and openai-compatible APIs
    if "anthropic" in provider_lower:
        return "langchain_anthropic:ChatAnthropic"
    # Everything else uses OpenAI-compatible interface
    # (OpenAI, Moonshot, MiniMax-OpenAI, vLLM, etc.)
    return "langchain_openai:ChatOpenAI"


def _infer_api_key_env_var(model_class: str) -> str:
    """Infer API key environment variable name from model class.

    Default convention: OPENAI_API_KEY for OpenAI-compatible APIs,
    ANTHROPIC_API_KEY for Anthropic APIs.
    Can be overridden via LLM_API_KEY_ENV_VAR env var.
    """
    if "anthropic" in model_class.lower():
        return "ANTHROPIC_API_KEY"
    return "OPENAI_API_KEY"


def _resolve_base_url() -> str | None:
    """Resolve base URL from environment variables.

    Priority (highest first):
    1. LLM_BASE_URL - Generic override
    2. {PROVIDER}_BASE_URL - Provider-specific (e.g., OPENAI_BASE_URL, ANTHROPIC_BASE_URL)
    3. None - Use SDK default
    """
    # Generic override takes highest priority
    if base_url := os.environ.get("LLM_BASE_URL"):
        return base_url

    # Provider-specific base URLs
    for env_var in [
        "OPENAI_BASE_URL",
        "ANTHROPIC_BASE_URL",
        "MOONSHOT_BASE_URL",
        "MINIMAX_BASE_URL",
    ]:
        if base_url := os.environ.get(env_var):
            return base_url

    return None


def _resolve_api_key(api_key_env_var: str) -> str | None:
    """Resolve API key from environment variable.

    Falls back to common API key env vars if the specific one is not set.
    """
    # Try the specific env var first
    if api_key := os.environ.get(api_key_env_var):
        return api_key

    # Fall back to common env vars
    for fallback_var in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_KEY"]:
        if api_key := os.environ.get(fallback_var):
            return api_key

    return None


def infer_env_runtime_model() -> RuntimeModel:
    """Infer runtime model configuration purely from environment.

    Required env vars:
    - LLM_MODEL: The model name to use (e.g., "gpt-4o", "kimi-k2.5", "MiniMax-M2.7")

    Optional env vars (with sensible defaults):
    - LLM_PROVIDER: Provider hint for convention-based defaults (default: "openai")
    - LLM_MODEL_CLASS: Full LangChain model class path (default: inferred from provider)
    - LLM_API_KEY_ENV_VAR: Environment variable name for API key (default: inferred from model_class)
    - LLM_BASE_URL / {PROVIDER}_BASE_URL: API base URL (default: None = SDK default)
    - LLM_DISPLAY_NAME: Human-readable display name (default: model name)
    - LLM_DESCRIPTION: Model description (default: None)
    - LLM_SUPPORTS_VISION: Whether model supports vision (default: true)

    Examples:
    # OpenAI
    LLM_MODEL=gpt-4o LLM_PROVIDER=openai OPENAI_API_KEY=sk-...

    # Moonshot (OpenAI-compatible)
    LLM_MODEL=kimi-k2.5 LLM_PROVIDER=openai OPENAI_API_KEY=sk-... OPENAI_BASE_URL=https://api.moonshot.cn/v1

    # MiniMax (Anthropic-compatible)
    LLM_MODEL=MiniMax-M2.7 LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-... ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic/v1

    # Custom (full override)
    LLM_MODEL=my-model LLM_MODEL_CLASS=langchain_openai:ChatOpenAI LLM_API_KEY_ENV_VAR=CUSTOM_API_KEY CUSTOM_API_KEY=xxx
    """
    model_name = os.environ.get("LLM_MODEL", "").strip()
    if not model_name:
        raise RuntimeConfigError(
            "LLM_MODEL is required. Set it in .env file or environment.\n"
            "Examples:\n"
            "  LLM_MODEL=gpt-4o\n"
            "  LLM_MODEL=kimi-k2.5\n"
            "  LLM_MODEL=MiniMax-M2.7"
        )

    # Get or infer model class
    provider_hint = os.environ.get("LLM_PROVIDER", "openai").strip()
    model_class = os.environ.get("LLM_MODEL_CLASS", "").strip()
    if not model_class:
        model_class = _infer_model_class(provider_hint)

    # Get or infer API key env var name
    api_key_env_var = os.environ.get("LLM_API_KEY_ENV_VAR", "").strip()
    if not api_key_env_var:
        api_key_env_var = _infer_api_key_env_var(model_class)

    # Resolve configuration
    base_url = _resolve_base_url()
    api_key = _resolve_api_key(api_key_env_var)

    if not api_key:
        raise RuntimeConfigError(
            f"API key not found. Tried: {api_key_env_var}, OPENAI_API_KEY, ANTHROPIC_API_KEY, LLM_API_KEY\n"
            f"Set one of these environment variables with your API key."
        )

    # Vision support (default true, can be disabled)
    supports_vision = os.environ.get("LLM_SUPPORTS_VISION", "true").lower() in ("true", "1", "yes")
    # Thinking support (default false)
    supports_thinking = os.environ.get("LLM_SUPPORTS_THINKING", "false").lower() in ("true", "1", "yes")

    return RuntimeModel(
        name=model_name,
        provider=provider_hint,
        model=model_name,
        display_name=os.environ.get("LLM_DISPLAY_NAME") or model_name,
        description=os.environ.get("LLM_MODEL_DESCRIPTION"),
        model_class=model_class,
        api_key_env_var=api_key_env_var,
        base_url=base_url,
        supports_vision=supports_vision,
        supports_thinking=supports_thinking,
        source=ENV_MODEL_SOURCE,
    )


def _gateway_base_url() -> str:
    """Return the SwarmMind LLM Gateway base URL."""
    from swarmmind.services.gateway_key import get_gateway_base_url

    return get_gateway_base_url()


def seed_env_provider() -> None:
    """Seed the database with a provider from environment variables (backward compat).

    If LlmProviderDB already has entries, this is a no-op so that user-managed
    providers take precedence over legacy .env configuration.
    """
    from swarmmind.models import LlmProviderModelEntry
    from swarmmind.repositories.llm_provider import LlmProviderRepository

    provider_repo = LlmProviderRepository()
    if provider_repo.count() > 0:
        return

    try:
        runtime_model = infer_env_runtime_model()
    except RuntimeConfigError:
        return

    api_key = _resolve_api_key(runtime_model.api_key_env_var)
    if not api_key:
        return

    # Normalize provider name for litellm model identifier
    provider_type = runtime_model.provider.lower()
    litellm_model = f"{provider_type}/{runtime_model.model}"

    provider_repo.create(
        name=f"Env {provider_type}",
        provider_type=provider_type,
        api_key=api_key,
        base_url=runtime_model.base_url,
        is_default=True,
        models=[
            LlmProviderModelEntry(
                model_name=runtime_model.name,
                litellm_model=litellm_model,
                display_name=runtime_model.display_name,
                supports_vision=runtime_model.supports_vision,
                supports_thinking=runtime_model.supports_thinking,
            ),
        ],
    )


def _sync_providers_to_catalog() -> None:
    """Bulk-sync all enabled provider models into RuntimeModelDB as gateway entries."""
    from swarmmind.db import session_scope
    from swarmmind.db_models import RuntimeModelAssignmentDB, RuntimeModelDB
    from swarmmind.repositories.llm_provider import LlmProviderRepository

    provider_repo = LlmProviderRepository()
    providers = provider_repo.get_enabled_providers_with_models()
    gateway_url = _gateway_base_url()

    with session_scope() as session:
        # Disable old gateway-sourced entries
        old_models = session.exec(
            select(RuntimeModelDB).where(RuntimeModelDB.source == "gateway"),
        ).all()
        for m in old_models:
            m.enabled = 0

        # Upsert provider models
        default_model_name: str | None = None
        for provider in providers:
            for m in provider.models:
                if not m.is_enabled:
                    continue
                if provider.is_default and default_model_name is None:
                    default_model_name = m.model_name

                db_model = session.get(RuntimeModelDB, m.model_name)
                if db_model is None:
                    db_model = RuntimeModelDB(
                        name=m.model_name,
                        provider=provider.provider_type,
                        model=m.model_name,
                        display_name=m.display_name or m.model_name,
                        model_class="langchain_openai:ChatOpenAI",
                        api_key_env_var="SWARMMIND_GATEWAY_KEY",
                        base_url=gateway_url,
                        supports_vision=int(m.supports_vision),
                        supports_thinking=int(m.supports_thinking),
                        enabled=1,
                        source="gateway",
                    )
                    session.add(db_model)
                else:
                    db_model.provider = provider.provider_type
                    db_model.model = m.model_name
                    db_model.display_name = m.display_name or m.model_name
                    db_model.model_class = "langchain_openai:ChatOpenAI"
                    db_model.api_key_env_var = "SWARMMIND_GATEWAY_KEY"
                    db_model.base_url = gateway_url
                    db_model.supports_vision = int(m.supports_vision)
                    db_model.supports_thinking = int(m.supports_thinking)
                    db_model.enabled = 1
                    db_model.source = "gateway"

        # Rebuild assignments for anonymous subject
        old_assignments = session.exec(
            select(RuntimeModelAssignmentDB).where(
                RuntimeModelAssignmentDB.subject_type == ANONYMOUS_SUBJECT_TYPE,
                RuntimeModelAssignmentDB.subject_id == ANONYMOUS_SUBJECT_ID,
            ),
        ).all()
        for a in old_assignments:
            session.delete(a)

        for provider in providers:
            for m in provider.models:
                if not m.is_enabled:
                    continue
                is_default = m.model_name == default_model_name
                assignment = RuntimeModelAssignmentDB(
                    subject_type=ANONYMOUS_SUBJECT_TYPE,
                    subject_id=ANONYMOUS_SUBJECT_ID,
                    model_name=m.model_name,
                    is_default=1 if is_default else 0,
                )
                session.add(assignment)

        session.commit()


def sync_env_runtime_model() -> RuntimeModel:
    """Mirror providers from DB into the runtime catalog.

    Backward-compat alias: previously this synced a single env model.
    Now it seeds from .env (if DB is empty) and syncs all provider models.
    """
    seed_env_provider()
    _sync_providers_to_catalog()

    # Fetch the default model directly without triggering another sync
    from swarmmind.db import session_scope
    from swarmmind.db_models import RuntimeModelAssignmentDB, RuntimeModelDB

    with session_scope() as session:
        assignment = session.exec(
            select(RuntimeModelAssignmentDB).where(
                RuntimeModelAssignmentDB.subject_type == ANONYMOUS_SUBJECT_TYPE,
                RuntimeModelAssignmentDB.subject_id == ANONYMOUS_SUBJECT_ID,
                RuntimeModelAssignmentDB.is_default == 1,
            ),
        ).first()
        if assignment is not None:
            db_model = session.get(RuntimeModelDB, assignment.model_name)
            if db_model is not None and db_model.enabled == 1:
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
                    supports_thinking=bool(db_model.supports_thinking),
                    source=db_model.source,
                )

        # Fallback: return first enabled model
        first = session.exec(
            select(RuntimeModelDB).where(RuntimeModelDB.enabled == 1),
        ).first()
        if first is not None:
            return RuntimeModel(
                name=first.name,
                provider=first.provider,
                model=first.model,
                display_name=first.display_name,
                description=first.description,
                model_class=first.model_class,
                api_key_env_var=first.api_key_env_var,
                base_url=first.base_url,
                supports_vision=bool(first.supports_vision),
                supports_thinking=bool(first.supports_thinking),
                source=first.source,
            )

    # No models at all — raise a clear error
    raise RuntimeConfigError(
        "No runtime models are available. Add an LLM provider via POST /llm-providers or set LLM_MODEL in .env."
    )


def list_enabled_runtime_models() -> list[RuntimeModel]:
    """Return all enabled models that should be injected into DeerFlow config."""
    sync_env_runtime_model()
    repo = RuntimeCatalogRepository()
    return repo.list_enabled_models()


def list_models_for_subject(
    subject_type: str = ANONYMOUS_SUBJECT_TYPE,
    subject_id: str = ANONYMOUS_SUBJECT_ID,
) -> list[RuntimeSelectableModel]:
    """Return the models available to the given subject."""
    sync_env_runtime_model()
    repo = RuntimeCatalogRepository()
    return repo.list_models_for_subject(subject_type, subject_id)


def resolve_model_for_subject(
    requested_model_name: str | None,
    subject_type: str = ANONYMOUS_SUBJECT_TYPE,
    subject_id: str = ANONYMOUS_SUBJECT_ID,
) -> RuntimeSelectableModel:
    """Validate a requested model or fall back to the subject default."""
    models = list_models_for_subject(subject_type=subject_type, subject_id=subject_id)
    if not models:
        raise RuntimeConfigError(f"No runtime models are assigned to {subject_type}:{subject_id}.")

    if requested_model_name:
        for model in models:
            if model.name == requested_model_name:
                return model
        raise RuntimeConfigError(f"Model '{requested_model_name}' is not assigned to {subject_type}:{subject_id}.")

    for model in models:
        if model.is_default:
            return model

    return models[0]
