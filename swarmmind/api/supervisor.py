"""Supervisor REST API — FastAPI server for human oversight."""

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from swarmmind.api.conversation_routes import (
    ClarificationResponseRequest as ConversationClarificationResponseRequest,
)
from swarmmind.api.conversation_routes import (
    ConversationRouteDeps,
    build_conversation_router,
)
from swarmmind.config import ACTION_TIMEOUT_SECONDS, API_HOST, API_PORT
from swarmmind.context_broker import (
    derive_situation_tag,
    dispatch,
    record_supervisor_decision,
)
from swarmmind.db import init_db, seed_default_agents
from swarmmind.models import (
    Conversation,
    ConversationListResponse,
    ConversationRuntimeOptions,
    GoalRequest,
    Message,
    MessageListResponse,
    PendingResponse,
    RejectRequest,
    RuntimeModelCatalogResponse,
    RuntimeModelOption,
    SendMessageRequest,
    StrategyEntry,
    StrategyResponse,
    SupervisorDecision,
)
from swarmmind.renderer import render_status
from swarmmind.repositories.action_proposal import (
    ActionProposalRepository,
    _db_to_action_proposal,
)
from swarmmind.repositories.conversation import ConversationRepository
from swarmmind.repositories.memory import MemoryRepository
from swarmmind.repositories.message import MessageRepository
from swarmmind.repositories.strategy import StrategyRepository
from swarmmind.services.conversation_execution import ConversationExecutionService
from swarmmind.services.conversation_support import (
    ConversationSupportService,
    generate_title_with_deerflow,
)
from swarmmind.services.conversation_trace_service import ConversationTraceService
from swarmmind.services.lifecycle import run_cleanup_scanner, startup_lifecycle
from swarmmind.services.runtime_support import RuntimeSupportService
from swarmmind.services.stream_events import (
    general_agent_status_labels as service_general_agent_status_labels,
)
from swarmmind.services.stream_events import (
    serialize_stream_event as service_serialize_stream_event,
)
from swarmmind.services.stream_events import (
    task_card_title as service_task_card_title,
)
from swarmmind.services.stream_events import (
    task_status_from_result as service_task_status_from_result,
)
from swarmmind.services.stream_events import (
    tool_activity_label as service_tool_activity_label,
)
from swarmmind.services.stream_events import (
    translate_general_agent_event as service_translate_general_agent_event,
)

conversation_repo = ConversationRepository()
message_repo = MessageRepository()
action_proposal_repo = ActionProposalRepository()
strategy_repo = StrategyRepository()
memory_repo = MemoryRepository()
conversation_support = ConversationSupportService(
    conversation_repo=conversation_repo,
    message_repo=message_repo,
    title_generator=generate_title_with_deerflow,
)
runtime_support = RuntimeSupportService(conversation_repo=conversation_repo)
conversation_trace_service = ConversationTraceService(conversation_repo=conversation_repo)


def _generate_title_with_deerflow(user_msg: str, assistant_msg: str) -> tuple[str, str]:
    return generate_title_with_deerflow(user_msg, assistant_msg)


from swarmmind.agents.general_agent import DeerFlowRuntimeAdapter
from swarmmind.runtime import (
    ensure_default_runtime_instance,
)
from swarmmind.runtime.catalog import (
    ANONYMOUS_SUBJECT_ID,
    ANONYMOUS_SUBJECT_TYPE,
    list_models_for_subject,
    sync_env_runtime_model,
)

logger = logging.getLogger(__name__)

NEW_CONVERSATION_TITLE = "New Conversation"

# ---- Pydantic models ----


class StatusResponse(BaseModel):
    """Status response with summary and goal."""

    summary: str
    goal: str


class StrategyChangeApproveRequest(BaseModel):
    """Request to approve a strategy change."""

    change_id: str


# ---- FastAPI app ----


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Bootstrap API dependencies and launch background cleanup workers."""
    startup_lifecycle(
        init_db=init_db,
        seed_default_agents=seed_default_agents,
        sync_env_runtime_model=sync_env_runtime_model,
        ensure_default_runtime_instance=ensure_default_runtime_instance,
        cleanup_scanner=_cleanup_scanner,
        api_host=API_HOST,
        api_port=API_PORT,
    )
    yield


app = FastAPI(
    title="SwarmMind Supervisor API",
    version="0.1.0",
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

# ---- Timeout scanner ----


def _cleanup_scanner():
    """Background thread: clean up stale proposals and expired memory entries."""
    run_cleanup_scanner(
        action_proposal_repo=action_proposal_repo,
        memory_repo=memory_repo,
        action_timeout_seconds=ACTION_TIMEOUT_SECONDS,
        record_supervisor_decision=record_supervisor_decision,
        supervisor_timeout_decision=SupervisorDecision.TIMEOUT,
        lifecycle_logger=logger,
    )


# ---- Supervisor endpoints ----


@app.get("/pending")
def get_pending(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)) -> PendingResponse:
    """List pending action proposals (paginated)."""
    rows, total = action_proposal_repo.list_pending(limit=limit, offset=offset)
    items = [_db_to_action_proposal(row) for row in rows]
    return PendingResponse(items=items, total=total)


@app.post("/approve/{proposal_id}")
def approve(proposal_id: str) -> dict:
    """Approve an action proposal."""
    action_proposal_repo.approve(proposal_id)
    record_supervisor_decision(proposal_id, SupervisorDecision.APPROVED)
    logger.info("Proposal %s approved by supervisor", proposal_id)
    return {"status": "approved", "id": proposal_id}


@app.post("/reject/{proposal_id}")
def reject(proposal_id: str, body: RejectRequest | None = None):
    """Reject an action proposal."""
    action_proposal_repo.reject_proposal(proposal_id)
    record_supervisor_decision(proposal_id, SupervisorDecision.REJECTED)
    logger.info("Proposal %s rejected by supervisor", proposal_id)
    reason = body.reason if body else None
    return {"status": "rejected", "id": proposal_id, "reason": reason}


@app.get("/status")
def get_status(goal: str = Query(..., max_length=2000)):
    """LLM Status Renderer: given a goal, read shared context and
    generate a human-readable status summary (Phase 1: prose only).
    """
    try:
        summary = render_status(goal)
        return StatusResponse(summary=summary, goal=goal)
    except Exception as e:
        logger.error("Status renderer error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/strategy")
def get_strategy() -> StrategyResponse:
    """View the strategy routing table."""
    rows = strategy_repo.list_all()
    entries = [
        StrategyEntry(
            situation_tag=row.situation_tag,
            agent_id=row.agent_id,
            success_count=row.success_count,
            failure_count=row.failure_count,
        )
        for row in rows
    ]
    return StrategyResponse(entries=entries)


@app.post("/dispatch")
def post_dispatch(body: GoalRequest):
    """Submit a new goal for dispatch to an agent."""
    try:
        session_id = str(uuid.uuid4())
        result = dispatch(
            body.goal,
            user_id="supervisor",
            session_id=session_id,
        )
        return result
    except Exception as e:
        logger.error("Dispatch error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}


@app.get("/ready")
def ready() -> dict[str, str]:
    """Readiness check: database plus DeerFlow runtime bundle."""
    runtime_instance = ensure_default_runtime_instance()
    return {
        "status": "ok",
        "runtime_profile_id": runtime_instance.runtime_profile_id,
        "runtime_instance_id": runtime_instance.runtime_instance_id,
    }


@app.get("/models")
def list_runtime_models() -> RuntimeModelCatalogResponse:
    """List runtime models available to the current anonymous visitor subject."""
    models = list_models_for_subject(
        subject_type=ANONYMOUS_SUBJECT_TYPE,
        subject_id=ANONYMOUS_SUBJECT_ID,
    )
    default_model = next((model.name for model in models if model.is_default), None)
    return RuntimeModelCatalogResponse(
        models=[
            RuntimeModelOption(
                name=model.name,
                provider=model.provider,
                model=model.model,
                display_name=model.display_name,
                description=model.description,
                supports_vision=model.supports_vision,
                is_default=model.is_default,
            )
            for model in models
        ],
        default_model=default_model,
        subject_type=ANONYMOUS_SUBJECT_TYPE,
        subject_id=ANONYMOUS_SUBJECT_ID,
    )


# ---- Conversation endpoints ----


def _db_to_conversation(conv) -> Conversation:
    return conversation_support.db_to_conversation(conv)


def _db_to_message(msg) -> Message:
    return conversation_support.db_to_message(msg)


def _serialize_stream_event(event_type: str, **payload) -> str:
    return service_serialize_stream_event(event_type, **payload)


def _tool_activity_label(tool_name: str, args: dict | None = None) -> str:
    return service_tool_activity_label(tool_name, args)


def _task_card_title(tool_args: dict | None) -> str:
    return service_task_card_title(tool_args)


def _task_status_from_result(content: str) -> tuple[str, str | None]:
    return service_task_status_from_result(content)


def _persist_user_message(conversation_id: str, content: str) -> Message:
    return conversation_support.persist_user_message(conversation_id, content)


def _persist_assistant_message(conversation_id: str, content: str) -> Message:
    return conversation_support.persist_assistant_message(conversation_id, content)


def _normalize_model_name(model_name: str | None) -> str | None:
    return runtime_support.normalize_model_name(model_name)


def _resolve_model_name_for_request(model_name: str | None) -> str:
    return runtime_support.resolve_model_name_for_request(model_name)


def _conversation_thread_id(conversation_id: str) -> str:
    return runtime_support.conversation_thread_id(conversation_id)


def _bind_conversation_runtime(conversation_id: str) -> tuple[object, str]:
    return runtime_support.bind_conversation_runtime(conversation_id)


def _format_runtime_error(exc: Exception) -> str:
    return runtime_support.format_runtime_error(exc)


def _resolve_runtime_options(body: SendMessageRequest) -> ConversationRuntimeOptions:
    return runtime_support.resolve_runtime_options(body)


def _general_agent_status_labels(runtime_options: ConversationRuntimeOptions) -> tuple[str, str]:
    return service_general_agent_status_labels(runtime_options)


def _translate_general_agent_event(
    event: dict,
    runtime_options: ConversationRuntimeOptions,
) -> list[str]:
    return service_translate_general_agent_event(event, runtime_options)


def _maybe_generate_conversation_title(conversation_id: str) -> None:
    conversation_support.maybe_generate_conversation_title(conversation_id, _generate_title_with_deerflow)


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
        persist_user_message_fn=_persist_user_message,
        persist_assistant_message_fn=_persist_assistant_message,
        maybe_generate_conversation_title_fn=_maybe_generate_conversation_title,
        bind_conversation_runtime_fn=_bind_conversation_runtime,
        format_runtime_error_fn=_format_runtime_error,
        resolve_runtime_options_fn=_resolve_runtime_options,
        general_agent_status_labels_fn=_general_agent_status_labels,
        translate_general_agent_event_fn=_translate_general_agent_event,
        serialize_stream_event_fn=_serialize_stream_event,
        db_to_message_fn=_db_to_message,
        execution_logger=logger,
    )


def _list_conversations() -> ConversationListResponse:
    rows = conversation_repo.list_all()
    items = [_db_to_conversation(row) for row in rows]
    return ConversationListResponse(items=items, total=len(items))


def _create_conversation(body: GoalRequest) -> Conversation:
    conv = conversation_repo.create(NEW_CONVERSATION_TITLE, "pending")
    return _db_to_conversation(conv)


def _get_conversation(conversation_id: str) -> Conversation:
    conv = conversation_repo.get_by_id(conversation_id)
    return _db_to_conversation(conv)


def _get_conversation_messages(conversation_id: str) -> MessageListResponse:
    conversation_repo.get_by_id(conversation_id)
    rows = message_repo.list_by_conversation(conversation_id)
    items = [_db_to_message(row) for row in rows]
    return MessageListResponse(items=items, total=len(items))


def _send_message(conversation_id: str, body: SendMessageRequest):
    return _conversation_execution_service().send_message(conversation_id, body)


def _delete_conversation(conversation_id: str) -> dict:
    conversation_repo.get_by_id(conversation_id)
    conversation_repo.delete(conversation_id)
    return {"status": "deleted", "id": conversation_id}


# ---- Collaboration Trace Endpoints ----


def _get_conversation_trace(conversation_id: str) -> dict:
    return conversation_trace_service.get_trace(conversation_id)


def _stream_conversation_message(conversation_id: str, body: SendMessageRequest):
    """Stream a ChatSession turn with SwarmMind runtime semantics."""
    yield from _conversation_execution_service().stream_message(conversation_id, body)


def _respond_to_clarification(conversation_id: str, tool_call_id: str, response: str) -> Message:
    return _conversation_execution_service().respond_to_clarification(
        conversation_id,
        tool_call_id,
        response,
    )


conversation_router, conversation_handlers = build_conversation_router(
    deps=ConversationRouteDeps(
        list_conversations=_list_conversations,
        create_conversation=_create_conversation,
        get_conversation=_get_conversation,
        get_conversation_messages=_get_conversation_messages,
        send_message=_send_message,
        delete_conversation=_delete_conversation,
        get_conversation_trace=_get_conversation_trace,
        stream_conversation_message=_stream_conversation_message,
        respond_to_clarification=_respond_to_clarification,
    ),
)

ClarificationResponseRequest = ConversationClarificationResponseRequest
list_conversations = conversation_handlers.list_conversations
create_conversation = conversation_handlers.create_conversation
get_conversation = conversation_handlers.get_conversation
get_conversation_messages = conversation_handlers.get_conversation_messages
send_message = conversation_handlers.send_message
delete_conversation = conversation_handlers.delete_conversation
get_conversation_trace = conversation_handlers.get_conversation_trace
_stream_conversation_message = conversation_handlers.stream_conversation_message
send_message_stream = conversation_handlers.send_message_stream
respond_to_clarification = conversation_handlers.respond_to_clarification

app.include_router(conversation_router)


# ---- Run ----

if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=API_HOST, port=API_PORT)
