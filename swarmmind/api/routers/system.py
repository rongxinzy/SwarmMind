"""System health and status routes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query

from swarmmind.models import HealthResponse, ReadyResponse, StatusResponse


@dataclass(frozen=True)
class SystemRouterDeps:
    ensure_default_runtime_instance: Callable
    render_status: Callable


def build_system_router(deps: SystemRouterDeps) -> APIRouter:
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

    @router.get("/status", tags=["supervisor"])
    def get_status(goal: str = Query(..., max_length=2000)) -> StatusResponse:
        """LLM Status Renderer: given a goal, read shared context and
        generate a human-readable status summary (Phase 1: prose only).
        """
        try:
            summary = deps.render_status(goal)
            return StatusResponse(summary=summary, goal=goal)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router
