"""Read-only layered memory routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from swarmmind.api.routers.mappers import db_to_memory_entry
from swarmmind.models import MemoryEntry, MemoryLayer, MemoryListResponse, MemoryScope


@dataclass(frozen=True)
class MemoryRouterDeps:
    """Dependencies for the memory router."""

    memory_repo: object


def build_memory_router(deps: MemoryRouterDeps) -> APIRouter:
    """Return read-only layered memory endpoints."""
    router = APIRouter()

    @router.get("/memory", tags=["memory"])
    def list_memory(
        layer: MemoryLayer | None = None,
        scope_id: str | None = None,
        tag: Annotated[list[str] | None, Query()] = None,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
    ) -> MemoryListResponse:
        """List layered-memory entries with optional filters."""
        rows = deps.memory_repo.list_by_filters(
            layer=layer.value if layer else None,
            scope_id=scope_id,
            tags=tag,
            limit=limit,
        )
        return MemoryListResponse(items=[db_to_memory_entry(row) for row in rows], total=len(rows))

    @router.get("/memory/{key}", tags=["memory"], responses={404: {"description": "Memory entry not found"}})
    def get_memory(
        key: str,
        layer: MemoryLayer,
        scope_id: str,
    ) -> MemoryEntry:
        """Read one layered-memory entry by exact layer, scope, and key."""
        entry = deps.memory_repo.read(MemoryScope(layer=layer, scope_id=scope_id), key)
        if entry is None:
            raise HTTPException(status_code=404, detail="Memory entry not found")
        return db_to_memory_entry(entry)

    return router
