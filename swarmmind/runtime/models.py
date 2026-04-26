"""Runtime control-plane models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeProfile:
    """Versionable runtime profile for a DeerFlow runtime."""

    runtime_profile_id: str
    provider: str
    model_name: str
    model_class: str
    api_key_env_var: str
    base_url: str | None = None
    supports_vision: bool = False


@dataclass(frozen=True)
class RuntimeModel:
    """Catalog entry for a DeerFlow-compatible model."""

    name: str
    provider: str
    model: str
    model_class: str
    api_key_env_var: str
    display_name: str | None = None
    description: str | None = None
    base_url: str | None = None
    supports_vision: bool = False
    supports_thinking: bool = False
    source: str = "manual"

    @property
    def capability_tags(self) -> list[str]:
        """Return product-facing capability tags.

        Mapping from DeerFlow boolean flags to semantic labels:
        - fast: no thinking, no vision
        - deep: supports thinking
        - planning: supports thinking (planning requires reasoning depth)
        - vision: supports vision
        """
        tags: list[str] = []
        if self.supports_thinking:
            tags.extend(["deep", "planning"])
        if self.supports_vision:
            tags.append("vision")
        if not tags:
            tags.append("fast")
        return tags


@dataclass(frozen=True)
class RuntimeSelectableModel(RuntimeModel):
    """Model entry visible to a specific subject with default selection metadata."""

    is_default: bool = False


@dataclass(frozen=True)
class RuntimeInstance:
    """Provisioned DeerFlow Runtime Instance metadata."""

    runtime_instance_id: str
    runtime_profile_id: str
    deployment_mode: str
    config_path: Path
    deer_flow_home: Path
    extensions_config_path: Path
    health_status: str = "ready"
