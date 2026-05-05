"""SQLModel ORM definitions for SwarmMind."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, Index, UniqueConstraint
from sqlmodel import Field, SQLModel

from swarmmind.time_utils import utc_now


class AgentDB(SQLModel, table=True):
    """Core agent registry."""

    __tablename__ = "agents"

    agent_id: str = Field(primary_key=True)
    domain: str
    system_prompt: str
    created_at: datetime | None = Field(default_factory=utc_now)


class SharedMemoryDB(SQLModel, table=True):
    """Shared-memory backing store.

    The physical table name remains ``working_memory`` for schema compatibility,
    but the runtime entry point is ``SharedMemory`` rather than a separate
    working-memory repository abstraction.
    """

    __tablename__ = "working_memory"

    key: str = Field(primary_key=True)
    value: str
    domain_tags: str | None = None
    last_writer_agent_id: str | None = None
    updated_at: datetime | None = Field(default_factory=utc_now)

    __table_args__ = (Index("idx_working_memory_tags", "domain_tags"),)


class StrategyTableDB(SQLModel, table=True):
    """Routing strategy: situation_tag -> agent_id with success tracking."""

    __tablename__ = "strategy_table"

    situation_tag: str = Field(primary_key=True)
    agent_id: str = Field(foreign_key="agents.agent_id")
    success_count: int = Field(default=0)
    failure_count: int = Field(default=0)


class EventLogDB(SQLModel, table=True):
    """Audit log of every goal dispatch."""

    __tablename__ = "event_log"

    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime | None = Field(default_factory=utc_now)
    goal: str
    situation_tag: str | None = None
    dispatched_agent_id: str | None = None
    action_proposal_id: str | None = None
    supervisor_decision: str | None = None  # 'approved' | 'rejected' | 'timeout'
    outcome: str | None = None  # 'success' | 'failure' | 'pending'
    latency_ms: int | None = None

    __table_args__ = (Index("idx_event_log_timestamp", "timestamp"),)


class ActionProposalDB(SQLModel, table=True):
    """Action proposals from agents (pending supervisor review)."""

    __tablename__ = "action_proposals"

    id: str = Field(primary_key=True)
    agent_id: str = Field(foreign_key="agents.agent_id")
    description: str
    target_resource: str | None = None
    preconditions: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    postconditions: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    confidence: float = Field(default=0.5)
    status: str = Field(default="pending")  # 'pending' | 'approved' | 'rejected' | 'executed'
    created_at: datetime | None = Field(default_factory=utc_now)

    __table_args__ = (Index("idx_action_proposals_status", "status"),)


class StrategyChangeProposalDB(SQLModel, table=True):
    """Strategy change proposals (routing updates, human-approved)."""

    __tablename__ = "strategy_change_proposals"

    id: str = Field(primary_key=True)
    situation_tag: str
    proposed_agent_id: str = Field(foreign_key="agents.agent_id")
    reason: str | None = None
    status: str = Field(default="pending")  # 'pending' | 'approved' | 'rejected'
    proposed_at: datetime | None = Field(default_factory=utc_now)


class ConversationDB(SQLModel, table=True):
    """Conversation sessions."""

    __tablename__ = "conversations"

    id: str = Field(primary_key=True)
    title: str
    title_status: str = Field(default="pending")
    title_source: str | None = None
    title_generated_at: datetime | None = None
    runtime_profile_id: str | None = None
    runtime_instance_id: str | None = None
    thread_id: str | None = None
    promoted_project_id: str | None = None
    created_at: datetime | None = Field(default_factory=utc_now)
    updated_at: datetime | None = Field(default_factory=utc_now)

    __table_args__ = (Index("idx_conversations_updated_at", "updated_at"),)


class MessageDB(SQLModel, table=True):
    """Messages within a conversation."""

    __tablename__ = "messages"

    id: str = Field(primary_key=True)
    conversation_id: str = Field(foreign_key="conversations.id")
    role: str
    content: str
    tool_call_id: str | None = None
    name: str | None = None
    run_id: str | None = None
    created_at: datetime | None = Field(default_factory=utc_now)

    __table_args__ = (Index("idx_messages_conversation", "conversation_id"),)


class MemoryEntryDB(SQLModel, table=True):
    """Layered memory entries (L4/L3/L2/L1)."""

    __tablename__ = "memory_entries"

    id: str = Field(primary_key=True)
    layer: str  # 'L4_user_soul', 'L3_project', 'L2_team', 'L1_tmp'
    scope_id: str
    key: str
    value: str
    tags: list[str] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime | None = Field(default_factory=utc_now)
    updated_at: datetime | None = Field(default_factory=utc_now)
    ttl: int | None = None
    version: int = Field(default=1)
    last_writer_agent_id: str | None = None

    __table_args__ = (
        UniqueConstraint("layer", "scope_id", "key"),
        Index("idx_memory_scope", "layer", "scope_id"),
        Index("idx_memory_layer_key", "layer", "scope_id", "key"),
    )


class SessionPromotionDB(SQLModel, table=True):
    """Session promotions: L1 -> L3/L2 migration records."""

    __tablename__ = "session_promotions"

    id: str = Field(primary_key=True)
    session_id: str
    target_layer: str  # 'L3_project' or 'L2_team'
    target_scope_id: str
    key_filter: list[str] | None = Field(default=None, sa_column=Column(JSON))
    promoted_at: datetime | None = Field(default_factory=utc_now)
    snapshot_count: int = Field(default=0)


class ProjectDB(SQLModel, table=True):
    """Formal project execution boundary."""

    __tablename__ = "projects"

    project_id: str = Field(primary_key=True)
    title: str
    goal: str | None = None
    scope: str | None = None
    constraints: str | None = None
    source_conversation_id: str | None = Field(default=None, foreign_key="conversations.id")
    conversation_id: str | None = Field(default=None, foreign_key="conversations.id")
    next_step: str | None = None
    phase: str | None = Field(default=None)  # e.g. "需求澄清", "设计", "开发", "测试", "交付"
    risk_level: str | None = Field(default=None)  # 'low' | 'medium' | 'high'
    status: str = Field(default="active")  # 'active' | 'archived'
    created_at: datetime | None = Field(default_factory=utc_now)
    updated_at: datetime | None = Field(default_factory=utc_now)

    __table_args__ = (
        Index("idx_projects_status", "status"),
        Index("idx_projects_source_conversation", "source_conversation_id"),
        Index("idx_projects_conversation", "conversation_id"),
    )


class ArtifactDB(SQLModel, table=True):
    """Artifact/evidence metadata for runs and conversations."""

    __tablename__ = "artifacts"

    artifact_id: str = Field(primary_key=True)
    conversation_id: str | None = Field(default=None, foreign_key="conversations.id")
    project_id: str | None = Field(default=None, foreign_key="projects.project_id")
    message_id: str | None = Field(default=None, foreign_key="messages.id")
    run_id: str | None = Field(default=None, foreign_key="runs.run_id")
    task_id: str | None = Field(default=None, foreign_key="tasks.task_id")
    author_role: str | None = None  # e.g. "产品专家", "架构专家"
    name: str | None = None
    path: str | None = None
    storage_uri: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    artifact_type: str | None = None  # 'write_file' | 'edit_file' | 'present_files' | 'other'
    created_at: datetime | None = Field(default_factory=utc_now)

    __table_args__ = (
        Index("idx_artifacts_conversation", "conversation_id"),
        Index("idx_artifacts_path", "path"),
        Index("idx_artifacts_project", "project_id"),
        Index("idx_artifacts_message", "message_id"),
        Index("idx_artifacts_run", "run_id"),
        Index("idx_artifacts_task", "task_id"),
    )


class RunDB(SQLModel, table=True):
    """Execution run anchored on project_id and conversation_id."""

    __tablename__ = "runs"

    run_id: str = Field(primary_key=True)
    project_id: str | None = Field(default=None, foreign_key="projects.project_id")
    conversation_id: str | None = Field(default=None, foreign_key="conversations.id")
    status: str = Field(default="running")  # 'running' | 'completed' | 'failed' | 'blocked'
    goal: str | None = None
    summary: str | None = None
    started_at: datetime | None = Field(default_factory=utc_now)
    completed_at: datetime | None = None

    __table_args__ = (
        Index("idx_runs_project", "project_id"),
        Index("idx_runs_conversation", "conversation_id"),
        Index("idx_runs_status", "status"),
    )


class CompactionHintDB(SQLModel, table=True):
    """Compaction hints: Phase 2 compression policy registry."""

    __tablename__ = "compaction_hints"

    id: str = Field(primary_key=True)
    scope_layer: str
    scope_id: str
    policy: str  # 'dedup', 'compress', 'archive'
    trigger_count: int = Field(default=0)
    fired_at: datetime | None = None
    created_at: datetime | None = Field(default_factory=utc_now)

    __table_args__ = (Index("idx_compaction_scope", "scope_layer", "scope_id"),)


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
    provider_type: str  # openai, anthropic, azure_openai, gemini, dashscope, ...
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
    litellm_model: str  # e.g. "openai/gpt-4o", "anthropic/claude-3-5-sonnet-20241022"
    display_name: str | None = None
    supports_vision: int = Field(default=0)
    supports_thinking: int = Field(default=0)
    fallback_model_names: str | None = None  # JSON list of model names, e.g. '["claude-3-5-sonnet"]'
    is_enabled: int = Field(default=1)
    created_at: datetime | None = Field(default_factory=utc_now)

    __table_args__ = (
        Index("idx_llm_provider_models_provider", "provider_id"),
        Index("idx_llm_provider_models_enabled", "is_enabled"),
    )


class AgentTeamTemplateDB(SQLModel, table=True):
    """Reusable agent team template: roles, skills, runtime preferences."""

    __tablename__ = "agent_team_templates"

    team_id: str = Field(primary_key=True)
    name: str
    description: str | None = None
    icon: str | None = None
    roles: str = "[]"  # JSON list[dict]
    default_workflow_id: str | None = None
    default_skills: str = "[]"  # JSON list[str]
    runtime_profile_prefs: str = "{}"  # JSON dict
    is_builtin: int = Field(default=1)
    is_enabled: int = Field(default=1)
    created_at: datetime | None = Field(default_factory=utc_now)
    updated_at: datetime | None = Field(default_factory=utc_now)

    __table_args__ = (
        Index("idx_agent_team_templates_builtin", "is_builtin"),
        Index("idx_agent_team_templates_enabled", "is_enabled"),
    )


class TaskDB(SQLModel, table=True):
    """Project task metadata for Kanban board."""

    __tablename__ = "tasks"

    task_id: str = Field(primary_key=True)
    project_id: str = Field(foreign_key="projects.project_id")
    run_id: str | None = Field(default=None, foreign_key="runs.run_id")
    title: str
    description: str | None = None
    status: str = Field(default="todo")  # 'todo' | 'in_progress' | 'blocked' | 'done'
    assignee_role: str | None = None
    source_workstream: str | None = None
    artifact_ids: list[str] | None = Field(default=None, sa_column=Column(JSON))
    priority: str | None = Field(default="medium")  # 'low' | 'medium' | 'high'
    created_at: datetime | None = Field(default_factory=utc_now)
    updated_at: datetime | None = Field(default_factory=utc_now)

    __table_args__ = (
        Index("idx_tasks_project", "project_id"),
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_run", "run_id"),
    )


class AuditLogDB(SQLModel, table=True):
    """Audit log for approvals, policy changes, and provenance."""

    __tablename__ = "audit_logs"

    audit_id: str = Field(primary_key=True)
    audit_type: str = Field(
        default="approval_decision"
    )  # 'approval_decision' | 'risk_identified' | 'policy_change' | 'member_permission_change' | 'run_resumed'
    project_id: str = Field(foreign_key="projects.project_id")
    run_id: str | None = Field(default=None, foreign_key="runs.run_id")
    approval_id: str | None = Field(default=None, foreign_key="approval_requests.approval_id")
    actor_id: str | None = None  # user_id or agent_id
    actor_type: str = Field(default="user")  # 'user' | 'agent' | 'system'
    decision: str | None = None  # 'approved' | 'rejected' | 'supplement_requested' | 'escalated'
    reason: str | None = None
    extra_data: dict[str, Any] | None = Field(default=None, sa_column=Column("metadata", JSON))
    timestamp: datetime | None = Field(default_factory=utc_now)

    __table_args__ = (
        Index("idx_audit_logs_project", "project_id"),
        Index("idx_audit_logs_run", "run_id"),
        Index("idx_audit_logs_approval", "approval_id"),
        Index("idx_audit_logs_timestamp", "timestamp"),
    )


class ProjectAgentTeamInstanceDB(SQLModel, table=True):
    """Team template instantiated inside a project."""

    __tablename__ = "project_agent_team_instances"

    instance_id: str = Field(primary_key=True)
    project_id: str = Field(foreign_key="projects.project_id", unique=True)
    team_template_id: str = Field(foreign_key="agent_team_templates.team_id")
    instance_config: str = "{}"  # JSON dict
    status: str = Field(default="active")  # 'active' | 'paused' | 'detached'
    created_at: datetime | None = Field(default_factory=utc_now)
    updated_at: datetime | None = Field(default_factory=utc_now)

    __table_args__ = (
        Index("idx_project_team_instances_project", "project_id"),
        Index("idx_project_team_instances_template", "team_template_id"),
    )


class ApprovalRequestDB(SQLModel, table=True):
    """Product-layer approval request for high-risk run governance."""

    __tablename__ = "approval_requests"

    approval_id: str = Field(primary_key=True)
    project_id: str = Field(foreign_key="projects.project_id")
    run_id: str | None = Field(default=None, foreign_key="runs.run_id")
    action_proposal_id: str | None = Field(default=None, foreign_key="action_proposals.id")
    title: str
    description: str | None = None
    risk_tier: str = Field(default="medium")  # 'low' | 'medium' | 'high'
    requested_capability: str | None = None
    evidence: str | None = None
    impact: str | None = None
    approver_role: str | None = None
    recovery_behavior: str | None = None
    status: str = Field(default="pending")  # 'pending' | 'approved' | 'rejected' | 'supplement_requested'
    decision_reason: str | None = None
    created_at: datetime | None = Field(default_factory=utc_now)
    updated_at: datetime | None = Field(default_factory=utc_now)

    __table_args__ = (
        Index("idx_approval_requests_project", "project_id"),
        Index("idx_approval_requests_run", "run_id"),
        Index("idx_approval_requests_status", "status"),
        Index("idx_approval_requests_risk", "risk_tier"),
    )
