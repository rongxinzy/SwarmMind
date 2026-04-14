"""Runtime model catalog backed by SQLite with env bootstrap for MVP.

Design Principle: Zero hardcoded model/provider details.
All model configuration comes from environment variables.
"""

from __future__ import annotations

import os

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
        source=ENV_MODEL_SOURCE,
    )


def sync_env_runtime_model() -> RuntimeModel:
    """Mirror the current env-configured model into the runtime catalog."""
    runtime_model = infer_env_runtime_model()
    repo = RuntimeCatalogRepository()
    repo.sync_env_model(
        runtime_model,
        anonymous_subject_type=ANONYMOUS_SUBJECT_TYPE,
        anonymous_subject_id=ANONYMOUS_SUBJECT_ID,
        env_source=ENV_MODEL_SOURCE,
    )
    return runtime_model


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
