"""Admin-only routes for user management and resource allocation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from swarmmind.models import (
    ResourceType,
    UserAllocation,
    UserAllocationCreateRequest,
    UserAllocationListResponse,
)
from swarmmind.repositories.user import UserRepository
from swarmmind.repositories.user_allocation import UserAllocationRepository

bearer_scheme = HTTPBearer(auto_error=False)


def _iso(value: Any) -> str:
    return value.isoformat() if value else ""


def _db_to_user_allocation(row: Any) -> UserAllocation:
    return UserAllocation(
        allocation_id=row.allocation_id,
        user_id=row.user_id,
        resource_type=row.resource_type,
        resource_name=row.resource_name,
        is_allowed=bool(row.is_allowed),
        created_at=_iso(row.created_at),
        updated_at=_iso(row.updated_at),
    )


@dataclass(frozen=True)
class AdminRouterDeps:
    """Dependencies for the admin router."""

    user_repo: UserRepository
    allocation_repo: UserAllocationRepository


def build_admin_router(deps: AdminRouterDeps) -> APIRouter:
    """Return an APIRouter for admin-only user and allocation management."""
    router = APIRouter()

    def current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),  # noqa: B008
    ) -> Any:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token",
            )
        user, _token = deps.user_repo.resolve_token(credentials.credentials)
        return user

    def require_admin(user: Any = Depends(current_user)) -> Any:  # noqa: B008
        if user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        return user

    @router.get("/admin/users/{user_id}/allocations", tags=["admin"])
    def list_user_allocations(
        user_id: str,
        _admin: Any = Depends(require_admin),  # noqa: B008
    ) -> UserAllocationListResponse:
        """List resource allocations for a user (admin only)."""
        deps.user_repo.get(user_id)
        rows = deps.allocation_repo.list_by_user(user_id)
        return UserAllocationListResponse(
            items=[_db_to_user_allocation(row) for row in rows],
            total=len(rows),
        )

    @router.put("/admin/users/{user_id}/allocations", tags=["admin"])
    def set_user_allocation(
        user_id: str,
        body: UserAllocationCreateRequest,
        _admin: Any = Depends(require_admin),  # noqa: B008
    ) -> UserAllocation:
        """Grant or revoke a resource allocation for a user (admin only)."""
        deps.user_repo.get(user_id)
        row = deps.allocation_repo.set(
            user_id=user_id,
            resource_type=body.resource_type.value,
            resource_name=body.resource_name,
            is_allowed=1 if body.is_allowed else 0,
        )
        return _db_to_user_allocation(row)

    @router.delete("/admin/users/{user_id}/allocations", tags=["admin"])
    def delete_user_allocation(
        user_id: str,
        resource_type: ResourceType,
        resource_name: str,
        _admin: Any = Depends(require_admin),  # noqa: B008
    ) -> dict[str, str]:
        """Delete a resource allocation for a user (admin only)."""
        deps.user_repo.get(user_id)
        deps.allocation_repo.delete_by_resource(
            user_id=user_id,
            resource_type=resource_type.value,
            resource_name=resource_name,
        )
        return {"status": "deleted", "user_id": user_id}

    return router
