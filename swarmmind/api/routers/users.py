"""Local users and token authentication routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from swarmmind.api.routers.mappers import db_to_user
from swarmmind.models import (
    AuthToken,
    CurrentUserResponse,
    DeleteUserResponse,
    LoginRequest,
    LogoutResponse,
    User,
    UserCreateRequest,
    UserListResponse,
    UserUpdateRequest,
)
from swarmmind.repositories.user import UserRepository
from swarmmind.services.auth import generate_api_token, hash_api_token

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class UsersRouterDeps:
    """Dependencies for the users/auth router."""

    user_repo: UserRepository


def build_users_router(deps: UsersRouterDeps) -> APIRouter:
    """Return an APIRouter for local users and API tokens."""
    router = APIRouter()

    def current_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> tuple[Any, Any]:  # noqa: B008
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
        return deps.user_repo.resolve_token(credentials.credentials)

    @router.get("/users", tags=["users"])
    def list_users() -> UserListResponse:
        """List local users."""
        rows = deps.user_repo.list_all()
        return UserListResponse(items=[db_to_user(row) for row in rows], total=len(rows))

    @router.post("/users", response_model=User, tags=["users"], status_code=status.HTTP_201_CREATED)
    def create_user(body: UserCreateRequest) -> User:
        """Create a local user."""
        row = deps.user_repo.create(
            email=body.email,
            password=body.password,
            display_name=body.display_name,
            role=body.role.value,
            status=body.status.value,
        )
        return db_to_user(row)

    @router.get("/users/{user_id}", tags=["users"])
    def get_user(user_id: str) -> User:
        """Get a local user."""
        return db_to_user(deps.user_repo.get(user_id))

    @router.patch("/users/{user_id}", tags=["users"])
    def update_user(user_id: str, body: UserUpdateRequest) -> User:
        """Update a local user."""
        row = deps.user_repo.update(
            user_id,
            email=body.email,
            password=body.password,
            display_name=body.display_name,
            role=body.role.value if body.role else None,
            status=body.status.value if body.status else None,
        )
        return db_to_user(row)

    @router.delete("/users/{user_id}", tags=["users"])
    def disable_user(user_id: str) -> DeleteUserResponse:
        """Disable a local user and revoke its tokens."""
        deps.user_repo.disable(user_id)
        return DeleteUserResponse(user_id=user_id)

    @router.post("/auth/login", tags=["auth"])
    def login(body: LoginRequest) -> AuthToken:
        """Exchange local credentials for a bearer token."""
        user = deps.user_repo.authenticate(email=body.email, password=body.password)
        token = generate_api_token()
        token_row = deps.user_repo.create_token(
            user_id=user.user_id,
            token_hash=hash_api_token(token),
            name=body.token_name,
        )
        return AuthToken(token_id=token_row.token_id, token=token, user=db_to_user(user))

    @router.get("/auth/me", tags=["auth"])
    def me(resolved: tuple[Any, Any] = Depends(current_token)) -> CurrentUserResponse:
        """Return the user attached to the current bearer token."""
        user, token = resolved
        return CurrentUserResponse(user=db_to_user(user), token_id=token.token_id)

    @router.post("/auth/logout", tags=["auth"])
    def logout(resolved: tuple[Any, Any] = Depends(current_token)) -> LogoutResponse:
        """Revoke the current bearer token."""
        _user, token = resolved
        deps.user_repo.revoke_token(token.token_id)
        return LogoutResponse(token_id=token.token_id)

    return router
