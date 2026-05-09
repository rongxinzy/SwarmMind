"""Runtime profile resolution for the local DeerFlow runtime."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from swarmmind.runtime.catalog import resolve_model_for_subject
from swarmmind.runtime.errors import RuntimeConfigError
from swarmmind.runtime.models import RuntimeProfile

if TYPE_CHECKING:
    from swarmmind.repositories.project_team import ProjectTeamInstanceRepository

logger = logging.getLogger(__name__)

DEFAULT_RUNTIME_PROFILE_ID = "local-default"


def resolve_project_runtime_profile(
    project_id: str,
    project_team_repo: ProjectTeamInstanceRepository,
) -> RuntimeProfile:
    """Resolve the RuntimeProfile for a project execution.

    If the project has a ``ProjectAgentTeamInstance`` with ``runtime_profile_id``
    set, that ID is used to select the model.  Otherwise falls back to the
    default environment-backed profile.

    This hook exists so future phases can attach per-project model overrides
    without changing the execution path.
    """
    instance = project_team_repo.get_by_project(project_id)
    if instance is not None and instance.runtime_profile_id:
        logger.info(
            "Project %s uses team-instance runtime profile: %s",
            project_id,
            instance.runtime_profile_id,
        )
        # runtime_profile_id is treated as a model name in the current catalog.
        # Full per-profile catalog lookup is a Phase D concern.
        try:
            selected_model = resolve_model_for_subject(
                requested_model_name=instance.runtime_profile_id
            )
            return RuntimeProfile(
                runtime_profile_id=instance.runtime_profile_id,
                provider=selected_model.provider,
                model_name=selected_model.name,
                model_class=selected_model.model_class,
                api_key_env_var=selected_model.api_key_env_var,
                base_url=selected_model.base_url,
                supports_vision=selected_model.supports_vision,
            )
        except Exception:
            logger.warning(
                "Failed to resolve team-instance profile %s for project %s; falling back to default",
                instance.runtime_profile_id,
                project_id,
            )

    return resolve_default_runtime_profile()


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
