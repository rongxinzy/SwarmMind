"""Supervisor REST API — FastAPI app assembly and router registration."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from swarmmind.api.chat_direct_routes import ChatDirectRouterDeps, build_chat_direct_router
from swarmmind.api.chat_routes import ChatRouterDeps, build_chat_router
from swarmmind.api.conversation_routes import (
    ClarificationResponseRequest as ConversationClarificationResponseRequest,
)
from swarmmind.api.conversation_routes import ConversationRouteDeps, build_conversation_router
from swarmmind.api.routers.admin import AdminRouterDeps, build_admin_router
from swarmmind.api.routers.organizations import (
    OrganizationsRouterDeps,
    build_organizations_router,
)
from swarmmind.api.routers.project_memberships import (
    ProjectMembershipRouterDeps,
    build_project_membership_router,
)
from swarmmind.api.routers.projects import ProjectsRouterDeps, build_projects_router
from swarmmind.api.routers.runtime_models import (
    build_runtime_models_router,
    list_runtime_models,  # noqa: F401  (re-export for tests)
)
from swarmmind.api.routers.system import SystemRouterDeps, build_system_router
from swarmmind.api.routers.users import UsersRouterDeps, build_users_router
from swarmmind.config import API_HOST, API_PORT
from swarmmind.db import init_db
from swarmmind.models import (
    Conversation,
    ConversationListResponse,
    ConversationRuntimeOptions,
    DeleteConversationResponse,
    Message,
    MessageListResponse,
    RecentConversationResponse,
    SendMessageRequest,
)
from swarmmind.repositories.artifact import ArtifactRepository
from swarmmind.repositories.conversation import ConversationRepository
from swarmmind.repositories.message import MessageRepository
from swarmmind.repositories.organization import OrganizationRepository
from swarmmind.repositories.project import ProjectRepository
from swarmmind.repositories.project_membership import ProjectMembershipRepository
from swarmmind.repositories.project_memory import ProjectMemoryRepository
from swarmmind.repositories.team import TeamRepository
from swarmmind.repositories.team_membership import TeamMembershipRepository
from swarmmind.repositories.user import UserRepository
from swarmmind.repositories.user_allocation import UserAllocationRepository
from swarmmind.runtime import ensure_default_runtime_instance
from swarmmind.runtime.catalog import sync_env_runtime_model
from swarmmind.services.conversation_execution import ConversationExecutionService
from swarmmind.services.conversation_support import (
    ConversationSupportService,
    generate_title_with_deerflow,
)
from swarmmind.services.runtime_support import RuntimeSupportService
from swarmmind.services.stream_events import (
    deerflow_runtime_status_labels as _svc_deerflow_runtime_status_labels,
)
from swarmmind.services.stream_events import (
    serialize_stream_event as _svc_serialize_stream_event,
)
from swarmmind.services.stream_events import (
    translate_deerflow_runtime_event as _svc_translate_deerflow_runtime_event,
)

logger = logging.getLogger(__name__)

NEW_CONVERSATION_TITLE = "New Conversation"
DeerFlowRuntime = None

# ---- Singletons ----

conversation_repo = ConversationRepository()
message_repo = MessageRepository()
project_repo = ProjectRepository()
project_membership_repo = ProjectMembershipRepository()
project_memory_repo = ProjectMemoryRepository()
artifact_repo = ArtifactRepository()
user_repo = UserRepository()
organization_repo = OrganizationRepository()
team_repo = TeamRepository()
team_membership_repo = TeamMembershipRepository()
user_allocation_repo = UserAllocationRepository()

conversation_support = ConversationSupportService(
    conversation_repo=conversation_repo,
    message_repo=message_repo,
    title_generator=generate_title_with_deerflow,
)
runtime_support = RuntimeSupportService(conversation_repo=conversation_repo)


def _generate_title_with_deerflow(user_msg: str, assistant_msg: str) -> tuple[str, str]:
    return generate_title_with_deerflow(user_msg, assistant_msg)


# ---- FastAPI app ----


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Bootstrap API dependencies."""
    logger.info("SwarmMind API startup: init_db")
    init_db()
    logger.info("SwarmMind API startup: sync_env_runtime_model")
    sync_env_runtime_model()
    logger.info("SwarmMind API startup: ensure_default_runtime_instance")
    ensure_default_runtime_instance()
    logger.info("SwarmMind API startup complete")
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
    global DeerFlowRuntime  # noqa: PLW0603
    if DeerFlowRuntime is None:
        from swarmmind.agents.deerflow_runtime import DeerFlowRuntime as _DeerFlowRuntime

        DeerFlowRuntime = _DeerFlowRuntime

    return ConversationExecutionService(
        conversation_repo=conversation_repo,
        message_repo=message_repo,
        runtime_cls=DeerFlowRuntime,
        persist_user_message_fn=conversation_support.persist_user_message,
        persist_assistant_message_fn=conversation_support.persist_assistant_message,
        maybe_generate_conversation_title_fn=lambda cid: conversation_support.maybe_generate_conversation_title(
            cid, _generate_title_with_deerflow
        ),
        bind_conversation_runtime_fn=runtime_support.bind_conversation_runtime,
        format_runtime_error_fn=runtime_support.format_runtime_error,
        resolve_runtime_options_fn=_resolve_runtime_options,
        deerflow_runtime_status_labels_fn=_svc_deerflow_runtime_status_labels,
        translate_deerflow_runtime_event_fn=_svc_translate_deerflow_runtime_event,
        serialize_stream_event_fn=_svc_serialize_stream_event,
        db_to_message_fn=conversation_support.db_to_message,
        execution_logger=logger,
        artifact_repo=artifact_repo,
    )


def _stream_conversation_message(conversation_id: str, body: SendMessageRequest):
    yield from _conversation_execution_service().stream_message(conversation_id, body)


def _stream_native_conversation_message(conversation_id: str, body: SendMessageRequest):
    yield from _conversation_execution_service().stream_native_message(conversation_id, body)


def _stream_native_project_message(_project_id: str, conversation_id: str, body: SendMessageRequest):
    # Project-scoped chat reuses the same execution path; project_id is resolved upstream.
    yield from _conversation_execution_service().stream_native_message(conversation_id, body)


def _respond_to_clarification(conversation_id: str, tool_call_id: str, response: str) -> Message:
    return _conversation_execution_service().respond_to_clarification(conversation_id, tool_call_id, response)


def _list_conversations() -> ConversationListResponse:
    rows = conversation_repo.list_all()
    return ConversationListResponse(
        items=[conversation_support.db_to_conversation(r) for r in rows],
        total=len(rows),
    )


def _create_conversation(body) -> Conversation:
    conv = conversation_repo.create(
        body.title or NEW_CONVERSATION_TITLE,
        "pending",
        session_type=body.session_type.value if body.session_type else "task",
    )
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
send_message_stream = conversation_handlers.send_message_stream
respond_to_clarification = conversation_handlers.respond_to_clarification
search_conversations = conversation_handlers.search_conversations
export_conversation = conversation_handlers.export_conversation

# ---- Include all routers ----

app.include_router(conversation_router)

app.include_router(
    build_chat_router(
        ChatRouterDeps(
            conversation_repo=conversation_repo,
            project_repo=project_repo,
            conversation_support=conversation_support,
            artifact_repo=artifact_repo,
            stream_native_conversation_message=_stream_native_conversation_message,
            stream_native_project_message=_stream_native_project_message,
            resolve_runtime_options=_resolve_runtime_options,
        )
    )
)

app.include_router(
    build_chat_direct_router(
        ChatDirectRouterDeps(
            conversation_repo=conversation_repo,
            message_repo=message_repo,
            conversation_support=conversation_support,
        )
    )
)

app.include_router(build_users_router(UsersRouterDeps(user_repo=user_repo)))

app.include_router(
    build_system_router(
        SystemRouterDeps(
            ensure_default_runtime_instance=ensure_default_runtime_instance,
        )
    )
)

app.include_router(build_runtime_models_router())

app.include_router(
    build_projects_router(
        ProjectsRouterDeps(
            project_repo=project_repo,
            conversation_repo=conversation_repo,
            conversation_support=conversation_support,
            memory_repo=project_memory_repo,
            artifact_repo=artifact_repo,
        )
    )
)

app.include_router(
    build_project_membership_router(
        ProjectMembershipRouterDeps(
            project_repo=project_repo,
            membership_repo=project_membership_repo,
        )
    )
)

app.include_router(
    build_organizations_router(
        OrganizationsRouterDeps(
            org_repo=organization_repo,
            team_repo=team_repo,
            membership_repo=team_membership_repo,
            user_repo=user_repo,
        )
    )
)

app.include_router(
    build_admin_router(
        AdminRouterDeps(
            user_repo=user_repo,
            allocation_repo=user_allocation_repo,
        )
    )
)

# ---- LLM gateway & provider routes ----

from swarmmind.api.llm_gateway_routes import router as _gateway_router
from swarmmind.api.llm_provider_routes import router as _provider_router

app.include_router(_gateway_router)
app.include_router(_provider_router)

# ---- Run ----

if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="info")
