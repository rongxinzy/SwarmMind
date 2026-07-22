"""Organization, team, and team membership routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from swarmmind.models import (
    Organization,
    OrganizationCreateRequest,
    OrganizationListResponse,
    OrganizationUpdateRequest,
    Team,
    TeamCreateRequest,
    TeamListResponse,
    TeamMembership,
    TeamMembershipCreateRequest,
    TeamMembershipListResponse,
    TeamMembershipUpdateRequest,
    TeamUpdateRequest,
)
from swarmmind.repositories.organization import OrganizationRepository
from swarmmind.repositories.team import TeamRepository
from swarmmind.repositories.team_membership import TeamMembershipRepository
from swarmmind.repositories.user import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


def _iso(value: Any) -> str:
    return value.isoformat() if value else ""


def _db_to_organization(row: Any) -> Organization:
    return Organization(
        organization_id=row.organization_id,
        name=row.name,
        owner_user_id=row.owner_user_id,
        status=row.status,
        created_at=_iso(row.created_at),
        updated_at=_iso(row.updated_at),
    )


def _db_to_team(row: Any) -> Team:
    return Team(
        team_id=row.team_id,
        organization_id=row.organization_id,
        name=row.name,
        status=row.status,
        created_at=_iso(row.created_at),
        updated_at=_iso(row.updated_at),
    )


def _db_to_team_membership(row: Any) -> TeamMembership:
    return TeamMembership(
        membership_id=row.membership_id,
        team_id=row.team_id,
        user_id=row.user_id,
        role=row.role,
        status=row.status,
        created_at=_iso(row.created_at),
        updated_at=_iso(row.updated_at),
    )


@dataclass(frozen=True)
class OrganizationsRouterDeps:
    """Dependencies for the organizations router."""

    org_repo: OrganizationRepository
    team_repo: TeamRepository
    membership_repo: TeamMembershipRepository
    user_repo: UserRepository


def build_organizations_router(deps: OrganizationsRouterDeps) -> APIRouter:
    """Return an APIRouter for organization and team management."""
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

    @router.get("/organizations", tags=["organizations"])
    def list_organizations(_admin: Any = Depends(require_admin)) -> OrganizationListResponse:  # noqa: B008
        """List all organizations (admin only)."""
        rows = deps.org_repo.list_all()
        return OrganizationListResponse(items=[_db_to_organization(row) for row in rows], total=len(rows))

    @router.post(
        "/organizations",
        tags=["organizations"],
        status_code=status.HTTP_201_CREATED,
    )
    def create_organization(
        body: OrganizationCreateRequest,
        _admin: Any = Depends(require_admin),  # noqa: B008
    ) -> Organization:
        """Create an organization (admin only)."""
        # Ensure owner exists
        deps.user_repo.get(body.owner_user_id)
        row = deps.org_repo.create(
            name=body.name,
            owner_user_id=body.owner_user_id,
        )
        return _db_to_organization(row)

    @router.get("/organizations/{organization_id}", tags=["organizations"])
    def get_organization(
        organization_id: str,
        _admin: Any = Depends(require_admin),  # noqa: B008
    ) -> Organization:
        """Get an organization (admin only)."""
        return _db_to_organization(deps.org_repo.get(organization_id))

    @router.patch("/organizations/{organization_id}", tags=["organizations"])
    def update_organization(
        organization_id: str,
        body: OrganizationUpdateRequest,
        _admin: Any = Depends(require_admin),  # noqa: B008
    ) -> Organization:
        """Update an organization (admin only)."""
        if body.owner_user_id is not None:
            deps.user_repo.get(body.owner_user_id)
        row = deps.org_repo.update(
            organization_id,
            name=body.name,
            owner_user_id=body.owner_user_id,
            status=body.status.value if body.status else None,
        )
        return _db_to_organization(row)

    @router.delete("/organizations/{organization_id}", tags=["organizations"])
    def delete_organization(
        organization_id: str,
        _admin: Any = Depends(require_admin),  # noqa: B008
    ) -> dict[str, str]:
        """Archive an organization (admin only)."""
        deps.org_repo.delete(organization_id)
        return {"status": "archived", "organization_id": organization_id}

    @router.get("/organizations/{organization_id}/teams", tags=["teams"])
    def list_teams(
        organization_id: str,
        _admin: Any = Depends(require_admin),  # noqa: B008
    ) -> TeamListResponse:
        """List teams in an organization (admin only)."""
        rows = deps.team_repo.list_by_organization(organization_id)
        return TeamListResponse(items=[_db_to_team(row) for row in rows], total=len(rows))

    @router.post(
        "/organizations/{organization_id}/teams",
        tags=["teams"],
        status_code=status.HTTP_201_CREATED,
    )
    def create_team(
        organization_id: str,
        body: TeamCreateRequest,
        _admin: Any = Depends(require_admin),  # noqa: B008
    ) -> Team:
        """Create a team in an organization (admin only)."""
        deps.org_repo.get(organization_id)
        row = deps.team_repo.create(
            organization_id=organization_id,
            name=body.name,
        )
        return _db_to_team(row)

    @router.get("/teams/{team_id}", tags=["teams"])
    def get_team(
        team_id: str,
        _admin: Any = Depends(require_admin),  # noqa: B008
    ) -> Team:
        """Get a team (admin only)."""
        return _db_to_team(deps.team_repo.get(team_id))

    @router.patch("/teams/{team_id}", tags=["teams"])
    def update_team(
        team_id: str,
        body: TeamUpdateRequest,
        _admin: Any = Depends(require_admin),  # noqa: B008
    ) -> Team:
        """Update a team (admin only)."""
        row = deps.team_repo.update(
            team_id,
            name=body.name,
            status=body.status.value if body.status else None,
        )
        return _db_to_team(row)

    @router.delete("/teams/{team_id}", tags=["teams"])
    def delete_team(
        team_id: str,
        _admin: Any = Depends(require_admin),  # noqa: B008
    ) -> dict[str, str]:
        """Archive a team (admin only)."""
        deps.team_repo.delete(team_id)
        return {"status": "archived", "team_id": team_id}

    @router.get("/teams/{team_id}/members", tags=["team memberships"])
    def list_team_members(
        team_id: str,
        _admin: Any = Depends(require_admin),  # noqa: B008
    ) -> TeamMembershipListResponse:
        """List members of a team (admin only)."""
        rows = deps.membership_repo.list_by_team(team_id)
        return TeamMembershipListResponse(
            items=[_db_to_team_membership(row) for row in rows],
            total=len(rows),
        )

    @router.post(
        "/teams/{team_id}/members",
        tags=["team memberships"],
        status_code=status.HTTP_201_CREATED,
    )
    def add_team_member(
        team_id: str,
        body: TeamMembershipCreateRequest,
        _admin: Any = Depends(require_admin),  # noqa: B008
    ) -> TeamMembership:
        """Add a user to a team (admin only)."""
        deps.team_repo.get(team_id)
        deps.user_repo.get(body.user_id)
        row = deps.membership_repo.create(
            team_id=team_id,
            user_id=body.user_id,
            role=body.role.value,
            status=body.status.value,
        )
        return _db_to_team_membership(row)

    @router.patch("/teams/{team_id}/members/{membership_id}", tags=["team memberships"])
    def update_team_member(
        team_id: str,
        membership_id: str,
        body: TeamMembershipUpdateRequest,
        _admin: Any = Depends(require_admin),  # noqa: B008
    ) -> TeamMembership:
        """Update a team membership (admin only)."""
        row = deps.membership_repo.update(
            membership_id,
            role=body.role.value if body.role else None,
            status=body.status.value if body.status else None,
        )
        return _db_to_team_membership(row)

    @router.delete("/teams/{team_id}/members/{membership_id}", tags=["team memberships"])
    def remove_team_member(
        team_id: str,
        membership_id: str,
        _admin: Any = Depends(require_admin),  # noqa: B008
    ) -> dict[str, str]:
        """Remove a user from a team (admin only)."""
        deps.membership_repo.delete(membership_id)
        return {"status": "removed", "team_id": team_id, "membership_id": membership_id}

    return router
