"""System health and status routes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import APIRouter

from swarmmind.models import HealthResponse, ReadyResponse


@dataclass(frozen=True)
class SystemRouterDeps:
    """Dependencies for the system router."""

    ensure_default_runtime_instance: Callable


def build_system_router(deps: SystemRouterDeps) -> APIRouter:
    """Return an APIRouter for health and readiness endpoints."""
    router = APIRouter()

    @router.get("/health", tags=["system"])
    def health() -> HealthResponse:
        """Health check endpoint."""
        return HealthResponse(timestamp=datetime.now(UTC).isoformat())

    @router.get("/ready", tags=["system"])
    def ready() -> ReadyResponse:
        """Readiness check: database plus DeerFlow runtime bundle."""
        runtime_instance = deps.ensure_default_runtime_instance()
        return ReadyResponse(
            runtime_profile_id=runtime_instance.runtime_profile_id,
            runtime_instance_id=runtime_instance.runtime_instance_id,
        )

    return router
