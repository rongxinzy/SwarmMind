"""Runtime profile resolution for the local DeerFlow runtime."""

from __future__ import annotations

import os

from swarmmind.runtime.catalog import resolve_model_for_subject
from swarmmind.runtime.errors import RuntimeConfigError
from swarmmind.runtime.models import RuntimeProfile

DEFAULT_RUNTIME_PROFILE_ID = "local-default"


def resolve_default_runtime_profile() -> RuntimeProfile:
    """Resolve the single MVP runtime profile from environment-backed config."""
    from swarmmind.services.gateway_key import ensure_gateway_key_in_env

    selected_model = resolve_model_for_subject(requested_model_name=None)
    api_key_env_var = selected_model.api_key_env_var

    if api_key_env_var == "SWARMMIND_GATEWAY_KEY":
        ensure_gateway_key_in_env()
    else:
        # Legacy direct-provider mode (fallback)
        api_key = os.environ.get(api_key_env_var)
        if not api_key:
            raise RuntimeConfigError(f"Missing {api_key_env_var} for DeerFlow runtime.")

    return RuntimeProfile(
        runtime_profile_id=DEFAULT_RUNTIME_PROFILE_ID,
        provider=selected_model.provider,
        model_name=selected_model.name,
        model_class=selected_model.model_class,
        api_key_env_var=selected_model.api_key_env_var,
        base_url=selected_model.base_url,
        supports_vision=selected_model.supports_vision,
    )
