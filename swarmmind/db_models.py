"""SQLModel ORM definitions for SwarmMind."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy import JSON, Column, Index
from sqlmodel import Field, SQLModel

from swarmmind.time_utils import utc_now


class ConversationDB(SQLModel, table=True):
    """Conversation sessions."""

    __tablename__ = "conversations"

    id: str = Field(primary_key=True)
    session_type: str = Field(default="task")  # "chat" or "task"
    project_id: str | None = Field(default=None, foreign_key="projects.project_id")
    title: str
    title_status: str = Field(default="pending")
    title_source: str | None = None
    title_generated_at: datetime | None = None
    runtime_profile_id: str | None = None
    runtime_instance_id: str | None = None
    thread_id: str | None = None
    is_project_bound: int = Field(default=0)  # 1 when bound to a project via ProjectDB.conversation_id
    created_at: datetime | None = Field(default_factory=utc_now)
    updated_at: datetime | None = Field(default_factory=utc_now)

    __table_args__ = (
        Index("idx_conversations_updated_at", "updated_at"),
        Index("idx_conversations_project", "project_id"),
    )


class MessageDB(SQLModel, table=True):
    """Messages within a conversation."""

    __tablename__ = "messages"

    id: str = Field(primary_key=True)
    conversation_id: str = Field(foreign_key="conversations.id")
    role: str
    content: str
    tool_call_id: str | None = None
    name: str | None = None
    native_payload: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime | None = Field(default_factory=utc_now)

    __table_args__ = (Index("idx_messages_conversation", "conversation_id"),)


class ProjectDB(SQLModel, table=True):
    """Formal project execution boundary."""

    __tablename__ = "projects"

    project_id: str = Field(primary_key=True)
    title: str
    goal: str | None = None
    scope: str | None = None
    constraints: str | None = None
    conversation_id: str | None = Field(default=None, foreign_key="conversations.id")
    next_step: str | None = None
    phase: str | None = Field(default=None)
    risk_level: str | None = Field(default=None)
    status: str = Field(default="active")
    created_at: datetime | None = Field(default_factory=utc_now)
    updated_at: datetime | None = Field(default_factory=utc_now)

    __table_args__ = (
        Index("idx_projects_status", "status"),
        Index("idx_projects_conversation", "conversation_id"),
    )


class UserDB(SQLModel, table=True):
    """Local user identity for CLI/API authentication."""

    __tablename__ = "users"

    user_id: str = Field(primary_key=True)
    email: str
    username: str | None = Field(default=None, index=True)
    display_name: str | None = None
    password_hash: str | None = None
    role: str = Field(default="member")
    status: str = Field(default="active")
    created_at: datetime | None = Field(default_factory=utc_now)
    updated_at: datetime | None = Field(default_factory=utc_now)
    last_login_at: datetime | None = None

    __table_args__ = (
        Index("idx_users_email", "email", unique=True),
        Index("idx_users_username", "username", unique=True),
        Index("idx_users_status", "status"),
        Index("idx_users_role", "role"),
    )


class UserTokenDB(SQLModel, table=True):
    """Hashed bearer token attached to a local user."""

    __tablename__ = "user_tokens"

    token_id: str = Field(primary_key=True)
    user_id: str = Field(foreign_key="users.user_id")
    token_hash: str
    name: str | None = None
    status: str = Field(default="active")
    created_at: datetime | None = Field(default_factory=utc_now)
    last_used_at: datetime | None = None
    expires_at: datetime | None = None

    __table_args__ = (
        Index("idx_user_tokens_user", "user_id"),
        Index("idx_user_tokens_hash", "token_hash", unique=True),
        Index("idx_user_tokens_status", "status"),
    )


class ArtifactDB(SQLModel, table=True):
    """Artifact/evidence metadata for conversations."""

    __tablename__ = "artifacts"

    artifact_id: str = Field(primary_key=True)
    conversation_id: str | None = Field(default=None, foreign_key="conversations.id")
    message_id: str | None = Field(default=None, foreign_key="messages.id")
    name: str | None = None
    path: str | None = None
    storage_uri: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    artifact_type: str | None = None
    created_at: datetime | None = Field(default_factory=utc_now)

    __table_args__ = (
        Index("idx_artifacts_conversation", "conversation_id"),
        Index("idx_artifacts_path", "path"),
        Index("idx_artifacts_message", "message_id"),
    )


class RuntimeModelDB(SQLModel, table=True):
    """Runtime model catalog."""

    __tablename__ = "runtime_models"

    name: str = Field(primary_key=True)
    provider: str
    model: str
    display_name: str | None = None
    description: str | None = None
    model_class: str
    api_key_env_var: str
    base_url: str | None = None
    supports_vision: int = Field(default=0)
    supports_thinking: int = Field(default=0)
    enabled: int = Field(default=1)
    source: str = Field(default="manual")
    created_at: datetime | None = Field(default_factory=utc_now)
    updated_at: datetime | None = Field(default_factory=utc_now)

    __table_args__ = (
        Index("idx_runtime_models_enabled", "enabled"),
        Index("idx_runtime_models_source", "source"),
    )


class RuntimeModelAssignmentDB(SQLModel, table=True):
    """Subject-to-model assignment, future-proof for tenant/user/group control."""

    __tablename__ = "runtime_model_assignments"

    subject_type: str = Field(primary_key=True)
    subject_id: str = Field(primary_key=True)
    model_name: str = Field(foreign_key="runtime_models.name", primary_key=True)
    is_default: int = Field(default=0)
    created_at: datetime | None = Field(default_factory=utc_now)

    __table_args__ = (Index("idx_runtime_model_assignments_subject", "subject_type", "subject_id"),)


class LlmProviderDB(SQLModel, table=True):
    """LLM provider account configuration."""

    __tablename__ = "llm_providers"

    provider_id: str = Field(primary_key=True)
    name: str
    provider_type: str
    api_key_encrypted: str
    base_url: str | None = None
    is_enabled: int = Field(default=1)
    is_default: int = Field(default=0)
    created_at: datetime | None = Field(default_factory=utc_now)
    updated_at: datetime | None = Field(default_factory=utc_now)

    __table_args__ = (
        Index("idx_llm_providers_enabled", "is_enabled"),
        Index("idx_llm_providers_default", "is_default"),
    )


class LlmProviderModelDB(SQLModel, table=True):
    """Models available through a specific provider account."""

    __tablename__ = "llm_provider_models"

    provider_id: str = Field(foreign_key="llm_providers.provider_id", primary_key=True)
    model_name: str = Field(primary_key=True)
    litellm_model: str
    display_name: str | None = None
    supports_vision: int = Field(default=0)
    supports_thinking: int = Field(default=0)
    fallback_model_names: str | None = None
    is_enabled: int = Field(default=1)
    created_at: datetime | None = Field(default_factory=utc_now)

    __table_args__ = (
        Index("idx_llm_provider_models_provider", "provider_id"),
        Index("idx_llm_provider_models_enabled", "is_enabled"),
    )


class ProjectMembershipDB(SQLModel, table=True):
    """Minimal project membership and RBAC boundary."""

    __tablename__ = "project_memberships"

    membership_id: str = Field(primary_key=True)
    project_id: str = Field(foreign_key="projects.project_id")
    member_id: str
    display_name: str | None = None
    role: str = Field(default="viewer")
    status: str = Field(default="active")
    created_at: datetime | None = Field(default_factory=utc_now)
    updated_at: datetime | None = Field(default_factory=utc_now)

    __table_args__ = (
        Index("idx_project_memberships_project", "project_id"),
        Index("idx_project_memberships_member", "member_id"),
        Index("idx_project_memberships_role", "role"),
        sa.Index("idx_project_memberships_project_member", "project_id", "member_id", unique=True),
    )


class ProjectMemoryDB(SQLModel, table=True):
    """Project-scoped shared memory key-value store."""

    __tablename__ = "project_memory"

    project_id: str = Field(foreign_key="projects.project_id", primary_key=True)
    key: str = Field(primary_key=True)
    value: str
    created_at: datetime | None = Field(default_factory=utc_now)
    updated_at: datetime | None = Field(default_factory=utc_now)

    __table_args__ = (Index("idx_project_memory_project", "project_id"),)
