"""DB row → Pydantic model mappers shared across domain routers."""

from __future__ import annotations

from swarmmind.models import (
    Artifact,
    Project,
    ProjectCapability,
    ProjectMemoryEntry,
    ProjectMembership,
    User,
)
from swarmmind.services.artifact_content import (
    is_virtual_user_data_path,
    normalize_virtual_path,
)


def db_to_artifact(art) -> Artifact:
    """Map an ArtifactDB row to an Artifact Pydantic model."""
    return Artifact(
        artifact_id=art.artifact_id,
        conversation_id=art.conversation_id,
        message_id=art.message_id,
        name=art.name,
        path=art.path or (normalize_virtual_path(art.name) if is_virtual_user_data_path(art.name) else None),
        storage_uri=art.storage_uri,
        mime_type=art.mime_type,
        size_bytes=art.size_bytes,
        artifact_type=art.artifact_type,
        created_at=art.created_at.isoformat() if art.created_at else "",
    )


_ROLE_CAPABILITIES: dict[str, list[ProjectCapability]] = {
    "owner": [
        ProjectCapability.VIEW_PROJECT,
        ProjectCapability.RUN_PROJECT,
        ProjectCapability.MANAGE_PROJECT,
        ProjectCapability.APPROVE_HIGH_RISK,
        ProjectCapability.MANAGE_MEMBERS,
    ],
    "editor": [
        ProjectCapability.VIEW_PROJECT,
        ProjectCapability.RUN_PROJECT,
        ProjectCapability.MANAGE_PROJECT,
    ],
    "approver": [
        ProjectCapability.VIEW_PROJECT,
        ProjectCapability.APPROVE_HIGH_RISK,
    ],
    "viewer": [
        ProjectCapability.VIEW_PROJECT,
    ],
}


def project_role_capabilities(role: str) -> list[ProjectCapability]:
    """Return capabilities granted to a project role."""
    return _ROLE_CAPABILITIES.get(role, [])


def db_to_project_membership(member) -> ProjectMembership:
    """Map a ProjectMembershipDB row to a ProjectMembership model."""
    return ProjectMembership(
        membership_id=member.membership_id,
        project_id=member.project_id,
        member_id=member.member_id,
        display_name=member.display_name,
        role=member.role,
        status=member.status,
        capabilities=project_role_capabilities(member.role) if member.status == "active" else [],
        created_at=member.created_at.isoformat() if member.created_at else "",
        updated_at=member.updated_at.isoformat() if member.updated_at else "",
    )


def db_to_user(user) -> User:
    """Map a UserDB row to a public User model."""
    return User(
        user_id=user.user_id,
        email=user.email,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        status=user.status,
        created_at=user.created_at.isoformat() if user.created_at else "",
        updated_at=user.updated_at.isoformat() if user.updated_at else "",
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )


def db_to_project(proj) -> Project:
    """Map a ProjectDB row to a Project Pydantic model."""
    return Project(
        project_id=proj.project_id,
        title=proj.title,
        goal=proj.goal,
        scope=proj.scope,
        constraints=proj.constraints,
        conversation_id=proj.conversation_id,
        next_step=proj.next_step,
        phase=proj.phase,
        risk_level=proj.risk_level,
        status=proj.status,
        created_at=proj.created_at.isoformat() if proj.created_at else "",
        updated_at=proj.updated_at.isoformat() if proj.updated_at else "",
    )


def db_to_project_memory(entry) -> ProjectMemoryEntry:
    """Map a ProjectMemoryDB row to a ProjectMemoryEntry model."""
    return ProjectMemoryEntry(
        project_id=entry.project_id,
        key=entry.key,
        value=entry.value,
        created_at=entry.created_at.isoformat() if entry.created_at else "",
        updated_at=entry.updated_at.isoformat() if entry.updated_at else "",
    )
