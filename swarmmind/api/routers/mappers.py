"""DB row → Pydantic model mappers shared across domain routers."""

from __future__ import annotations

import json

from swarmmind.models import (
    AgentTeamTemplate,
    ApprovalRequest,
    ApprovalStatus,
    Artifact,
    AuditLogEntry,
    Project,
    ProjectAgentTeamInstance,
    RiskTier,
    Run,
    Task,
    TeamRole,
)
from swarmmind.services.artifact_content import (
    is_virtual_user_data_path,
    normalize_virtual_path,
)


def db_to_run(run) -> Run:
    """Map a RunDB row to a Run Pydantic model."""
    return Run(
        run_id=run.run_id,
        project_id=run.project_id,
        conversation_id=run.conversation_id,
        status=run.status,
        goal=run.goal,
        summary=run.summary,
        started_at=run.started_at.isoformat() if run.started_at else "",
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
    )


def db_to_task(task) -> Task:
    """Map a TaskDB row to a Task Pydantic model."""
    return Task(
        task_id=task.task_id,
        project_id=task.project_id,
        run_id=task.run_id,
        step_key=getattr(task, "step_key", None),
        title=task.title,
        description=task.description,
        status=task.status,
        assignee_role=task.assignee_role,
        source_workstream=task.source_workstream,
        artifact_ids=task.artifact_ids or [],
        priority=task.priority,
        created_at=task.created_at.isoformat() if task.created_at else "",
        updated_at=task.updated_at.isoformat() if task.updated_at else "",
    )


def db_to_artifact(art) -> Artifact:
    """Map an ArtifactDB row to an Artifact Pydantic model."""
    return Artifact(
        artifact_id=art.artifact_id,
        conversation_id=art.conversation_id,
        project_id=art.project_id,
        message_id=art.message_id,
        run_id=art.run_id,
        task_id=art.task_id,
        author_role=art.author_role,
        name=art.name,
        path=art.path or (normalize_virtual_path(art.name) if is_virtual_user_data_path(art.name) else None),
        storage_uri=art.storage_uri,
        mime_type=art.mime_type,
        size_bytes=art.size_bytes,
        artifact_type=art.artifact_type,
        created_at=art.created_at.isoformat() if art.created_at else "",
    )


def db_to_approval_request(ar) -> ApprovalRequest:
    """Map an ApprovalRequestDB row to an ApprovalRequest Pydantic model."""
    return ApprovalRequest(
        approval_id=ar.approval_id,
        project_id=ar.project_id,
        run_id=ar.run_id,
        action_proposal_id=ar.action_proposal_id,
        title=ar.title,
        description=ar.description,
        risk_tier=RiskTier(ar.risk_tier),
        requested_capability=ar.requested_capability,
        evidence=ar.evidence,
        impact=ar.impact,
        approver_role=ar.approver_role,
        recovery_behavior=ar.recovery_behavior,
        status=ApprovalStatus(ar.status),
        decision_reason=ar.decision_reason,
        created_at=ar.created_at.isoformat() if ar.created_at else "",
        updated_at=ar.updated_at.isoformat() if ar.updated_at else "",
    )


def db_to_audit_log_entry(entry) -> AuditLogEntry:
    """Map an AuditLogDB row to an AuditLogEntry Pydantic model."""
    return AuditLogEntry(
        audit_id=entry.audit_id,
        audit_type=entry.audit_type,
        project_id=entry.project_id,
        run_id=entry.run_id,
        approval_id=entry.approval_id,
        actor_id=entry.actor_id,
        actor_type=entry.actor_type,
        decision=entry.decision,
        reason=entry.reason,
        metadata=entry.extra_data or {},
        timestamp=entry.timestamp.isoformat() if entry.timestamp else "",
    )


def db_to_team_template(team) -> AgentTeamTemplate:
    """Map an AgentTeamDB row to an AgentTeamTemplate Pydantic model."""
    return AgentTeamTemplate(
        team_id=team.team_id,
        name=team.name,
        description=team.description,
        icon=team.icon,
        roles=[TeamRole(**r) for r in json.loads(team.roles)] if team.roles else [],
        default_skills=json.loads(team.default_skills) if team.default_skills else [],
        runtime_profile_prefs=json.loads(team.runtime_profile_prefs) if team.runtime_profile_prefs else {},
        is_builtin=bool(team.is_builtin),
        is_enabled=bool(team.is_enabled),
        created_at=team.created_at.isoformat() if team.created_at else "",
        updated_at=team.updated_at.isoformat() if team.updated_at else "",
    )


def db_to_team_instance(instance, agent_team_repo) -> ProjectAgentTeamInstance:
    """Map a ProjectTeamInstanceDB row to a ProjectAgentTeamInstance Pydantic model."""
    template = agent_team_repo.get_by_id(instance.team_template_id)
    return ProjectAgentTeamInstance(
        instance_id=instance.instance_id,
        project_id=instance.project_id,
        team_template_id=instance.team_template_id,
        team_name=template.name,
        team_description=template.description,
        roles=[TeamRole(**r) for r in json.loads(template.roles)] if template.roles else [],
        instance_config=json.loads(instance.instance_config) if instance.instance_config else {},
        status=instance.status,
        created_at=instance.created_at.isoformat() if instance.created_at else "",
        updated_at=instance.updated_at.isoformat() if instance.updated_at else "",
    )


def db_to_project(proj, project_team_repo, agent_team_repo) -> Project:
    """Map a ProjectDB row to a Project Pydantic model."""
    team_instance = project_team_repo.get_by_project(proj.project_id)
    agent_team = db_to_team_instance(team_instance, agent_team_repo) if team_instance else None
    return Project(
        project_id=proj.project_id,
        title=proj.title,
        goal=proj.goal,
        scope=proj.scope,
        constraints=proj.constraints,
        source_conversation_id=proj.source_conversation_id,
        conversation_id=proj.conversation_id,
        next_step=proj.next_step,
        phase=proj.phase,
        risk_level=proj.risk_level,
        status=proj.status,
        created_at=proj.created_at.isoformat() if proj.created_at else "",
        updated_at=proj.updated_at.isoformat() if proj.updated_at else "",
        agent_team=agent_team,
    )
