"""Supervisor REST API — FastAPI app assembly and router registration."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from swarmmind.agents.general_agent import DeerFlowRuntimeAdapter
from swarmmind.api.conversation_routes import (
    ClarificationResponseRequest as ConversationClarificationResponseRequest,
)
from swarmmind.api.conversation_routes import ConversationRouteDeps, build_conversation_router
from swarmmind.api.routers.agent_teams import AgentTeamsRouterDeps, build_agent_teams_router
from swarmmind.api.routers.approvals import ApprovalsRouterDeps, build_approvals_router
from swarmmind.api.routers.audit_logs import AuditLogsRouterDeps, build_audit_logs_router
from swarmmind.api.routers.legacy_supervisor import LegacySupervisorRouterDeps, build_legacy_supervisor_router
from swarmmind.api.routers.memory import MemoryRouterDeps, build_memory_router
from swarmmind.api.routers.project_memberships import (
    ProjectMembershipRouterDeps,
    build_project_membership_router,
)
from swarmmind.api.routers.projects import ProjectsRouterDeps, build_projects_router
from swarmmind.api.routers.promotions import PromotionsRouterDeps, build_promotions_router
from swarmmind.api.routers.runs import RunsRouterDeps, build_runs_router
from swarmmind.api.routers.runtime_models import (
    build_runtime_models_router,
    list_runtime_models,  # noqa: F401  (re-export for tests)
)
from swarmmind.api.routers.system import SystemRouterDeps, build_system_router
from swarmmind.api.routers.users import UsersRouterDeps, build_users_router
from swarmmind.config import ACTION_TIMEOUT_SECONDS, API_HOST, API_PORT
from swarmmind.context_broker import derive_situation_tag, dispatch, record_supervisor_decision
from swarmmind.db import init_db, seed_builtin_agent_teams, seed_default_agents
from swarmmind.models import (
    Conversation,
    ConversationListResponse,
    ConversationRuntimeOptions,
    ConversationTraceResponse,
    DeleteConversationResponse,
    Message,
    MessageListResponse,
    RecentConversationResponse,
    SendMessageRequest,
    SupervisorDecision,
)
from swarmmind.renderer import render_status
from swarmmind.repositories.action_proposal import ActionProposalRepository
from swarmmind.repositories.agent_team import AgentTeamRepository
from swarmmind.repositories.approval_request import ApprovalRequestRepository
from swarmmind.repositories.artifact import ArtifactRepository
from swarmmind.repositories.audit_log import AuditLogRepository
from swarmmind.repositories.conversation import ConversationRepository
from swarmmind.repositories.memory import MemoryRepository
from swarmmind.repositories.message import MessageRepository
from swarmmind.repositories.project import ProjectRepository
from swarmmind.repositories.project_membership import ProjectMembershipRepository
from swarmmind.repositories.project_team import ProjectTeamInstanceRepository
from swarmmind.repositories.run import RunRepository
from swarmmind.repositories.strategy import StrategyRepository
from swarmmind.repositories.task import TaskRepository
from swarmmind.repositories.user import UserRepository
from swarmmind.runtime import ensure_default_runtime_instance
from swarmmind.runtime.catalog import sync_env_runtime_model
from swarmmind.services.conversation_execution import ConversationExecutionService
from swarmmind.services.conversation_support import (
    ConversationSupportService,
    generate_title_with_deerflow,
)
from swarmmind.services.conversation_trace_service import ConversationTraceService
from swarmmind.services.lifecycle import run_cleanup_scanner, startup_lifecycle
from swarmmind.services.message_trace_service import _default_message_trace_service
from swarmmind.services.run_context import RunContext
from swarmmind.services.run_lifecycle import RunLifecycleService
from swarmmind.services.runtime_support import RuntimeSupportService
from swarmmind.services.stream_events import (
    general_agent_status_labels as _svc_general_agent_status_labels,
)
from swarmmind.services.stream_events import (
    serialize_stream_event as _svc_serialize_stream_event,
)
from swarmmind.services.stream_events import (
    translate_general_agent_event as _svc_translate_general_agent_event,
)

logger = logging.getLogger(__name__)

NEW_CONVERSATION_TITLE = "New Conversation"

# ---- Singletons ----

conversation_repo = ConversationRepository()
message_repo = MessageRepository()
action_proposal_repo = ActionProposalRepository()
approval_request_repo = ApprovalRequestRepository()
strategy_repo = StrategyRepository()
memory_repo = MemoryRepository()
project_repo = ProjectRepository()
project_membership_repo = ProjectMembershipRepository()
artifact_repo = ArtifactRepository()
run_repo = RunRepository()
agent_team_repo = AgentTeamRepository()
project_team_repo = ProjectTeamInstanceRepository()
task_repo = TaskRepository()
audit_log_repo = AuditLogRepository()
user_repo = UserRepository()

conversation_support = ConversationSupportService(
    conversation_repo=conversation_repo,
    message_repo=message_repo,
    title_generator=generate_title_with_deerflow,
)
from swarmmind.services.audit_writer import AuditWriter

audit_writer = AuditWriter(audit_log_repo=audit_log_repo)
run_lifecycle_service = RunLifecycleService(run_repo=run_repo, audit_writer=audit_writer)
runtime_support = RuntimeSupportService(conversation_repo=conversation_repo)
conversation_trace_service = ConversationTraceService(conversation_repo=conversation_repo)
message_trace_service = _default_message_trace_service()


def _generate_title_with_deerflow(user_msg: str, assistant_msg: str) -> tuple[str, str]:
    return generate_title_with_deerflow(user_msg, assistant_msg)


# ---- Cleanup scanner ----


def _cleanup_scanner():
    run_cleanup_scanner(
        action_proposal_repo=action_proposal_repo,
        memory_repo=memory_repo,
        action_timeout_seconds=ACTION_TIMEOUT_SECONDS,
        record_supervisor_decision=record_supervisor_decision,
        supervisor_timeout_decision=SupervisorDecision.TIMEOUT,
        lifecycle_logger=logger,
    )


# ---- FastAPI app ----


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Bootstrap API dependencies and launch background cleanup workers."""
    startup_lifecycle(
        init_db=init_db,
        seed_default_agents=seed_default_agents,
        seed_builtin_agent_teams=seed_builtin_agent_teams,
        sync_env_runtime_model=sync_env_runtime_model,
        ensure_default_runtime_instance=ensure_default_runtime_instance,
        cleanup_scanner=_cleanup_scanner,
        api_host=API_HOST,
        api_port=API_PORT,
    )
    yield


app = FastAPI(
    title="SwarmMind Supervisor API",
    version="0.9.0",
    description="Human oversight interface for AI agent teams.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Conversation handler helpers ----


def _resolve_runtime_options(body: SendMessageRequest) -> ConversationRuntimeOptions:
    return runtime_support.resolve_runtime_options(body)


def _conversation_execution_service() -> ConversationExecutionService:
    return ConversationExecutionService(
        conversation_repo=conversation_repo,
        message_repo=message_repo,
        action_proposal_repo=action_proposal_repo,
        runtime_adapter_cls=DeerFlowRuntimeAdapter,
        dispatch_fn=dispatch,
        derive_situation_tag_fn=derive_situation_tag,
        record_supervisor_decision_fn=record_supervisor_decision,
        approved_decision=SupervisorDecision.APPROVED,
        persist_user_message_fn=lambda cid, content, run_id=None: conversation_support.persist_user_message(
            cid, content, run_id=run_id
        ),
        persist_assistant_message_fn=conversation_support.persist_assistant_message,
        maybe_generate_conversation_title_fn=lambda cid: conversation_support.maybe_generate_conversation_title(
            cid, _generate_title_with_deerflow
        ),
        bind_conversation_runtime_fn=runtime_support.bind_conversation_runtime,
        format_runtime_error_fn=runtime_support.format_runtime_error,
        resolve_runtime_options_fn=_resolve_runtime_options,
        general_agent_status_labels_fn=_svc_general_agent_status_labels,
        translate_general_agent_event_fn=_svc_translate_general_agent_event,
        serialize_stream_event_fn=_svc_serialize_stream_event,
        db_to_message_fn=conversation_support.db_to_message,
        execution_logger=logger,
        run_lifecycle_service=run_lifecycle_service,
        approval_request_repo=approval_request_repo,
    )


def _stream_conversation_message(conversation_id: str, body: SendMessageRequest):
    yield from _conversation_execution_service().stream_message(conversation_id, body)


def _stream_project_message(project_id: str, conversation_id: str, body: SendMessageRequest):
    run_context = RunContext.for_project(project_id, conversation_id)
    yield from _conversation_execution_service().stream_message(conversation_id, body, run_context=run_context)


def _respond_to_clarification(conversation_id: str, tool_call_id: str, response: str) -> Message:
    return _conversation_execution_service().respond_to_clarification(conversation_id, tool_call_id, response)


def _list_conversations() -> ConversationListResponse:
    rows = conversation_repo.list_all()
    return ConversationListResponse(
        items=[conversation_support.db_to_conversation(r) for r in rows],
        total=len(rows),
    )


def _create_conversation(body) -> Conversation:
    conv = conversation_repo.create(body.title or NEW_CONVERSATION_TITLE, "pending")
    return conversation_support.db_to_conversation(conv)


def _get_conversation(conversation_id: str, include_messages: bool = False) -> Conversation:
    conv = conversation_repo.get_by_id(conversation_id)
    conv_model = conversation_support.db_to_conversation(conv)
    if include_messages:
        rows = message_repo.list_by_conversation(conversation_id)
        conv_model.messages = [conversation_support.db_to_message(m) for m in rows]
    return conv_model


def _get_recent_conversation() -> RecentConversationResponse | None:
    conv = conversation_repo.get_recent_active(since_days=7)
    if conv is None:
        return None
    rows = message_repo.list_by_conversation(conv.id)
    return RecentConversationResponse(
        conversation=conversation_support.db_to_conversation(conv),
        messages=[conversation_support.db_to_message(m) for m in rows],
    )


def _get_conversation_messages(conversation_id: str) -> MessageListResponse:
    conversation_repo.get_by_id(conversation_id)
    rows = message_repo.list_by_conversation(conversation_id)
    items = [conversation_support.db_to_message(m) for m in rows]
    return MessageListResponse(items=items, total=len(items))


def _send_message(conversation_id: str, body: SendMessageRequest):
    return _conversation_execution_service().send_message(conversation_id, body)


def _delete_conversation(conversation_id: str) -> DeleteConversationResponse:
    conversation_repo.get_by_id(conversation_id)
    next_conv = conversation_repo.get_next_after(conversation_id)
    conversation_repo.delete(conversation_id)
    return DeleteConversationResponse(
        status="deleted",
        id=conversation_id,
        next_conversation_id=next_conv.id if next_conv is not None else None,
    )


def _get_conversation_trace(conversation_id: str) -> ConversationTraceResponse:
    return ConversationTraceResponse(
        conversation_id=conversation_id,
        trace=conversation_trace_service.get_trace(conversation_id),
    )


def _search_conversations(q: str, limit: int = 20) -> ConversationListResponse:
    rows = conversation_repo.search_by_query(q, limit=limit)
    return ConversationListResponse(
        items=[conversation_support.db_to_conversation(r) for r in rows],
        total=len(rows),
    )


def _export_conversation(conversation_id: str, fmt: str = "markdown") -> object:
    import json as _json
    from datetime import datetime as _dt

    from fastapi.responses import Response as _Response

    conv = conversation_repo.get_by_id(conversation_id)
    rows = message_repo.list_by_conversation(conversation_id)
    visible = [m for m in rows if m.role in ("user", "assistant")]

    if fmt == "json":
        data = {
            "id": conv.id,
            "title": conv.title,
            "created_at": str(conv.created_at) if conv.created_at else "",
            "updated_at": str(conv.updated_at) if conv.updated_at else "",
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "created_at": str(m.created_at) if m.created_at else "",
                }
                for m in visible
            ],
        }
        content = _json.dumps(data, ensure_ascii=False, indent=2)
        filename = f"conversation-{conv.id[:8]}.json"
        return _Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    now = _dt.now().strftime("%Y-%m-%d %H:%M")
    lines: list[str] = [f"# {conv.title}", "", f"*导出时间: {now}*", "", "---", ""]
    for msg in visible:
        label = "**用户**" if msg.role == "user" else "**SwarmMind**"
        lines.extend([f"{label}\n\n{msg.content}", ""])
    content = "\n".join(lines)
    filename = f"conversation-{conv.id[:8]}.md"
    return _Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---- Register conversation router ----

conversation_router, conversation_handlers = build_conversation_router(
    deps=ConversationRouteDeps(
        list_conversations=_list_conversations,
        create_conversation=_create_conversation,
        get_conversation=_get_conversation,
        get_recent_conversation=_get_recent_conversation,
        get_conversation_messages=_get_conversation_messages,
        send_message=_send_message,
        delete_conversation=_delete_conversation,
        get_conversation_trace=_get_conversation_trace,
        stream_conversation_message=_stream_conversation_message,
        respond_to_clarification=_respond_to_clarification,
        search_conversations=_search_conversations,
        export_conversation=_export_conversation,
    ),
)

# Backward-compat re-exports consumed by tests
ClarificationResponseRequest = ConversationClarificationResponseRequest
list_conversations = conversation_handlers.list_conversations
create_conversation = conversation_handlers.create_conversation
get_conversation = conversation_handlers.get_conversation
get_recent_conversation = conversation_handlers.get_recent_conversation
get_conversation_messages = conversation_handlers.get_conversation_messages
send_message = conversation_handlers.send_message
delete_conversation = conversation_handlers.delete_conversation
get_conversation_trace = conversation_handlers.get_conversation_trace
send_message_stream = conversation_handlers.send_message_stream
respond_to_clarification = conversation_handlers.respond_to_clarification
search_conversations = conversation_handlers.search_conversations
export_conversation = conversation_handlers.export_conversation

# ---- Include all routers ----

app.include_router(conversation_router)

app.include_router(build_users_router(UsersRouterDeps(user_repo=user_repo)))

app.include_router(
    build_system_router(
        SystemRouterDeps(
            ensure_default_runtime_instance=ensure_default_runtime_instance,
            render_status=render_status,
        )
    )
)

app.include_router(
    build_legacy_supervisor_router(
        LegacySupervisorRouterDeps(
            action_proposal_repo=action_proposal_repo,
            strategy_repo=strategy_repo,
            record_supervisor_decision=record_supervisor_decision,
            dispatch=dispatch,
        )
    )
)

app.include_router(build_runtime_models_router())

app.include_router(
    build_projects_router(
        ProjectsRouterDeps(
            project_repo=project_repo,
            task_repo=task_repo,
            run_repo=run_repo,
            artifact_repo=artifact_repo,
            approval_request_repo=approval_request_repo,
            audit_log_repo=audit_log_repo,
            agent_team_repo=agent_team_repo,
            project_team_repo=project_team_repo,
            conversation_repo=conversation_repo,
            stream_conversation_message=_stream_conversation_message,
            stream_project_message=_stream_project_message,
        )
    )
)

app.include_router(
    build_runs_router(
        RunsRouterDeps(
            run_repo=run_repo,
            project_repo=project_repo,
            conversation_repo=conversation_repo,
        )
    )
)

app.include_router(
    build_approvals_router(
        ApprovalsRouterDeps(
            approval_request_repo=approval_request_repo,
            project_repo=project_repo,
            run_repo=run_repo,
            audit_writer=audit_writer,
        )
    )
)

app.include_router(
    build_audit_logs_router(
        AuditLogsRouterDeps(
            audit_log_repo=audit_log_repo,
            project_repo=project_repo,
            run_repo=run_repo,
            approval_request_repo=approval_request_repo,
        )
    )
)

app.include_router(build_memory_router(MemoryRouterDeps(memory_repo=memory_repo)))

app.include_router(
    build_project_membership_router(
        ProjectMembershipRouterDeps(
            project_repo=project_repo,
            membership_repo=project_membership_repo,
            audit_writer=audit_writer,
        )
    )
)

app.include_router(
    build_agent_teams_router(
        AgentTeamsRouterDeps(
            agent_team_repo=agent_team_repo,
        )
    )
)

app.include_router(
    build_promotions_router(
        PromotionsRouterDeps(
            conversation_repo=conversation_repo,
            message_repo=message_repo,
            project_repo=project_repo,
            project_team_repo=project_team_repo,
            agent_team_repo=agent_team_repo,
            artifact_repo=artifact_repo,
            message_trace_service_fn=lambda: message_trace_service,
            runtime_support=runtime_support,
        )
    )
)

# ---- LLM gateway & provider routes ----

from swarmmind.api.llm_gateway_routes import router as _gateway_router
from swarmmind.api.llm_provider_routes import router as _provider_router
from swarmmind.api.routers.connectors import router as _connectors_router

app.include_router(_gateway_router)
app.include_router(_provider_router)
app.include_router(_connectors_router)

# ---- Run ----

if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=API_HOST, port=API_PORT)
