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
    ApproveResponse,
    Artifact,
    ArtifactListResponse,
    Conversation,
    ConversationListResponse,
    ConversationRuntimeOptions,
    ConversationTraceResponse,
    CreateConversationRequest,
    CreateRunRequest,
    DeleteConversationResponse,
    DeleteProjectResponse,
    DispatchResponse,
    ExtractArtifactsResponse,
    GoalRequest,
    HealthResponse,
    Message,
    MessageListResponse,
    PendingResponse,
    Project,
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectUpdateRequest,
    PromoteConversationRequest,
    ReadyResponse,
    RecentConversationResponse,
    RejectRequest,
    RejectResponse,
    Run,
    RunListResponse,
    RuntimeModelCatalogResponse,
    RuntimeModelOption,
    SendMessageRequest,
    StatusResponse,
    StrategyEntry,
    StrategyResponse,
    SupervisorDecision,
    TraceSummaryResponse,
)
from swarmmind.renderer import render_status
from swarmmind.repositories.action_proposal import (
    ActionProposalRepository,
    _db_to_action_proposal,
)
from swarmmind.repositories.artifact import ArtifactRepository
from swarmmind.repositories.conversation import ConversationRepository
from swarmmind.repositories.memory import MemoryRepository
from swarmmind.repositories.message import MessageRepository
from swarmmind.repositories.project import ProjectRepository
from swarmmind.repositories.run import RunRepository
from swarmmind.repositories.strategy import StrategyRepository
from swarmmind.services.conversation_execution import ConversationExecutionService
from swarmmind.services.conversation_support import (
    ConversationSupportService,
    generate_title_with_deerflow,
)
from swarmmind.services.conversation_trace_service import ConversationTraceService
from swarmmind.services.lifecycle import run_cleanup_scanner, startup_lifecycle
from swarmmind.services.message_trace_service import (
    MessageTraceService,
    _default_message_trace_service,
)
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
project_repo = ProjectRepository()
artifact_repo = ArtifactRepository()
run_repo = RunRepository()
conversation_support = ConversationSupportService(
    conversation_repo=conversation_repo,
    message_repo=message_repo,
    title_generator=generate_title_with_deerflow,
)
runtime_support = RuntimeSupportService(conversation_repo=conversation_repo)
conversation_trace_service = ConversationTraceService(conversation_repo=conversation_repo)
message_trace_service = _default_message_trace_service()


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


@app.get("/pending", tags=["supervisor"])
def get_pending(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)) -> PendingResponse:
    """List pending action proposals (paginated)."""
    rows, total = action_proposal_repo.list_pending(limit=limit, offset=offset)
    items = [_db_to_action_proposal(row) for row in rows]
    return PendingResponse(items=items, total=total)


@app.post("/approve/{proposal_id}", tags=["supervisor"], responses={404: {"description": "Proposal not found"}})
def approve(proposal_id: str) -> ApproveResponse:
    """Approve an action proposal."""
    action_proposal_repo.approve(proposal_id)
    record_supervisor_decision(proposal_id, SupervisorDecision.APPROVED)
    logger.info("Proposal %s approved by supervisor", proposal_id)
    return ApproveResponse(id=proposal_id)


@app.post("/reject/{proposal_id}", tags=["supervisor"], responses={404: {"description": "Proposal not found"}})
def reject(proposal_id: str, body: RejectRequest | None = None) -> RejectResponse:
    """Reject an action proposal."""
    action_proposal_repo.reject_proposal(proposal_id)
    record_supervisor_decision(proposal_id, SupervisorDecision.REJECTED)
    logger.info("Proposal %s rejected by supervisor", proposal_id)
    reason = body.reason if body else None
    return RejectResponse(id=proposal_id, reason=reason)


@app.get("/status", tags=["supervisor"])
def get_status(goal: str = Query(..., max_length=2000)) -> StatusResponse:
    """LLM Status Renderer: given a goal, read shared context and
    generate a human-readable status summary (Phase 1: prose only).
    """
    try:
        summary = render_status(goal)
        return StatusResponse(summary=summary, goal=goal)
    except Exception as e:
        logger.error("Status renderer error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/strategy", tags=["supervisor"])
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


@app.post("/dispatch", tags=["supervisor"])
def post_dispatch(body: GoalRequest) -> DispatchResponse:
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


@app.get("/health", tags=["system"])
def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(timestamp=datetime.now(UTC).isoformat())


@app.get("/ready", tags=["system"])
def ready() -> ReadyResponse:
    """Readiness check: database plus DeerFlow runtime bundle."""
    runtime_instance = ensure_default_runtime_instance()
    return ReadyResponse(
        runtime_profile_id=runtime_instance.runtime_profile_id,
        runtime_instance_id=runtime_instance.runtime_instance_id,
    )


@app.get("/models", tags=["runtime"])
@app.get("/runtime/models", tags=["runtime"])
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
                supports_thinking=model.supports_thinking,
                capability_tags=model.capability_tags,
                is_default=model.is_default,
            )
            for model in models
        ],
        default_model=default_model,
        subject_type=ANONYMOUS_SUBJECT_TYPE,
        subject_id=ANONYMOUS_SUBJECT_ID,
    )


# ---- Conversation endpoints ----


def _db_to_conversation(conv, messages: list[Message] | None = None) -> Conversation:
    conv_model = conversation_support.db_to_conversation(conv)
    if messages is not None:
        conv_model.messages = messages
    return conv_model


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


def _persist_user_message(conversation_id: str, content: str, run_id: str | None = None) -> Message:
    return conversation_support.persist_user_message(conversation_id, content, run_id=run_id)


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


def _create_conversation(body: CreateConversationRequest) -> Conversation:
    title = body.title or NEW_CONVERSATION_TITLE
    conv = conversation_repo.create(title, "pending")
    return _db_to_conversation(conv)


def _get_conversation(conversation_id: str, include_messages: bool = False) -> Conversation:
    conv = conversation_repo.get_by_id(conversation_id)
    messages = None
    if include_messages:
        rows = message_repo.list_by_conversation(conversation_id)
        messages = [_db_to_message(row) for row in rows]
    return _db_to_conversation(conv, messages=messages)


def _get_recent_conversation() -> RecentConversationResponse | None:
    conv = conversation_repo.get_recent_active(since_days=7)
    if conv is None:
        return None
    rows = message_repo.list_by_conversation(conv.id)
    messages = [_db_to_message(row) for row in rows]
    return RecentConversationResponse(
        conversation=_db_to_conversation(conv),
        messages=messages,
    )


def _get_conversation_messages(conversation_id: str) -> MessageListResponse:
    conversation_repo.get_by_id(conversation_id)
    rows = message_repo.list_by_conversation(conversation_id)
    items = [_db_to_message(row) for row in rows]
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


# ---- Collaboration Trace Endpoints ----


def _get_conversation_trace(conversation_id: str) -> ConversationTraceResponse:
    trace = conversation_trace_service.get_trace(conversation_id)
    return ConversationTraceResponse(conversation_id=conversation_id, trace=trace)


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
        get_recent_conversation=_get_recent_conversation,
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
get_recent_conversation = conversation_handlers.get_recent_conversation
get_conversation_messages = conversation_handlers.get_conversation_messages
send_message = conversation_handlers.send_message
delete_conversation = conversation_handlers.delete_conversation
get_conversation_trace = conversation_handlers.get_conversation_trace
_stream_conversation_message = conversation_handlers.stream_conversation_message
send_message_stream = conversation_handlers.send_message_stream
respond_to_clarification = conversation_handlers.respond_to_clarification

# ---- Project endpoints ----


def _db_to_project(proj) -> Project:
    return Project(
        project_id=proj.project_id,
        title=proj.title,
        goal=proj.goal,
        scope=proj.scope,
        constraints=proj.constraints,
        source_conversation_id=proj.source_conversation_id,
        next_step=proj.next_step,
        status=proj.status,
        created_at=proj.created_at.isoformat() if proj.created_at else "",
        updated_at=proj.updated_at.isoformat() if proj.updated_at else "",
    )


@app.get("/projects", tags=["projects"])
def list_projects() -> ProjectListResponse:
    """List all projects ordered by updated_at descending."""
    rows = project_repo.list_all()
    items = [_db_to_project(row) for row in rows]
    return ProjectListResponse(items=items, total=len(items))


@app.get("/projects/{project_id}", tags=["projects"], responses={404: {"description": "Project not found"}})
def get_project(project_id: str) -> Project:
    """Get a single project by ID."""
    proj = project_repo.get_by_id(project_id)
    return _db_to_project(proj)


@app.post("/projects", tags=["projects"])
def create_project(body: ProjectCreateRequest) -> Project:
    """Create a new project manually."""
    proj = project_repo.create(
        title=body.title,
        goal=body.goal,
        scope=body.scope,
        constraints=body.constraints,
        source_conversation_id=body.source_conversation_id,
        next_step=body.next_step,
    )
    return _db_to_project(proj)


@app.delete("/projects/{project_id}", tags=["projects"], responses={404: {"description": "Project not found"}})
def delete_project(project_id: str) -> DeleteProjectResponse:
    """Delete a project."""
    project_repo.get_by_id(project_id)
    project_repo.delete(project_id)
    return DeleteProjectResponse(project_id=project_id)


def _generate_project_seed_from_conversation(conversation_id: str, override: PromoteConversationRequest | None = None) -> dict:
    """Generate project seed fields from conversation messages.

    Strategy:
    1. Use explicit overrides from request body if provided.
    2. Fallback to conversation title and message heuristics.
    3. Future: integrate light LLM prompt for richer extraction.
    """
    conv = conversation_repo.get_by_id(conversation_id)
    messages = message_repo.list_by_conversation(conversation_id)

    user_msgs = [m for m in messages if m.role == "user"]
    assistant_msgs = [m for m in messages if m.role == "assistant"]

    # Title
    title = override.title if override and override.title else conv.title
    if title in ("New Conversation", NEW_CONVERSATION_TITLE) and user_msgs:
        first_user = user_msgs[0].content.strip()
        title = first_user[:50] if len(first_user) <= 50 else first_user[:47] + "..."

    # Goal: concatenate first few user messages
    goal = override.goal if override and override.goal else None
    if goal is None and user_msgs:
        parts = [m.content.strip() for m in user_msgs[:3]]
        goal = "\n".join(parts)
        if len(goal) > 2000:
            goal = goal[:1997] + "..."

    # Scope: default empty for minimal slice
    scope = override.scope if override and override.scope else None

    # Constraints: default empty
    constraints = override.constraints if override and override.constraints else None

    # Next step: derive from last assistant message if available
    next_step = override.next_step if override and override.next_step else None
    if next_step is None and assistant_msgs:
        last = assistant_msgs[-1].content.strip()
        # Take first sentence or first 100 chars as next-step hint
        sentence_end = max(last.find("."), last.find("。"), last.find("\n"))
        if sentence_end > 0:
            next_step = last[:sentence_end + 1]
        else:
            next_step = last[:100] + "..." if len(last) > 100 else last

    return {
        "title": title or "Untitled Project",
        "goal": goal,
        "scope": scope,
        "constraints": constraints,
        "source_conversation_id": conversation_id,
        "next_step": next_step,
    }


@app.post("/conversations/{conversation_id}/promote", tags=["conversations"], responses={404: {"description": "Conversation not found"}})
def promote_conversation(
    conversation_id: str,
    body: PromoteConversationRequest | None = None,
) -> Project:
    """Promote a ChatSession to a formal Project.

    - Source conversation remains as provenance.
    - Project receives structured seed, not a copied chat thread.
    - Falls back to minimal skeleton if generation fails.
    """
    # Ensure conversation exists
    conversation_repo.get_by_id(conversation_id)

    # Generate seed
    try:
        seed = _generate_project_seed_from_conversation(conversation_id, override=body)
    except Exception as e:
        logger.error("Project seed generation failed for %s: %s", conversation_id, e)
        # Minimal fallback skeleton
        seed = {
            "title": "Project from conversation",
            "goal": None,
            "scope": None,
            "constraints": None,
            "source_conversation_id": conversation_id,
            "next_step": "Review the source conversation and define next steps.",
        }

    # Create project
    proj = project_repo.create(**seed)

    # Link conversation -> project
    project_repo.link_conversation(proj.project_id, conversation_id)

    logger.info(
        "Conversation %s promoted to project %s (%s)",
        conversation_id,
        proj.project_id,
        proj.title,
    )
    return _db_to_project(proj)


# ---- Trace summary endpoint (F1) ----


@app.get("/conversations/{conversation_id}/messages/{message_id}/trace", tags=["conversations"], responses={404: {"description": "Conversation or message not found"}})
def get_message_trace(conversation_id: str, message_id: str) -> TraceSummaryResponse:
    """Return a readable trace summary for an assistant message.

    Integrates parsed checkpoint data from the trace service.
    Degrades to a minimal fallback when the trace store is empty or unreadable.
    """
    # Verify conversation exists
    conversation_repo.get_by_id(conversation_id)
    # Verify message exists and belongs to the conversation
    msg = message_repo.get_by_id(message_id)
    if msg.conversation_id != conversation_id:
        raise HTTPException(status_code=404, detail="Message not found in this conversation")

    # Real trace summary from checkpoint data
    try:
        return message_trace_service.get_summary(conversation_id, message_id)
    except Exception as exc:
        logger.warning("Trace summary failed for message %s: %s", message_id, exc)
        # Degraded fallback based on message metadata
        summary = "执行完成" if msg.run_id else "直接回复"
        return TraceSummaryResponse(
            steps_count=1 if msg.run_id else 0,
            subagent_calls_count=0,
            artifacts_count=0,
            blocked_points=[],
            summary=summary,
        )


# ---- Artifact endpoints ----


def _db_to_artifact(art) -> Artifact:
    return Artifact(
        artifact_id=art.artifact_id,
        conversation_id=art.conversation_id,
        message_id=art.message_id,
        name=art.name,
        artifact_type=art.artifact_type,
        created_at=art.created_at.isoformat() if art.created_at else "",
    )


@app.get("/conversations/{conversation_id}/artifacts", tags=["conversations"], responses={404: {"description": "Conversation not found"}})
def list_conversation_artifacts(conversation_id: str) -> ArtifactListResponse:
    """List artifacts for a conversation."""
    conversation_repo.get_by_id(conversation_id)
    rows = artifact_repo.list_by_conversation(conversation_id)
    return ArtifactListResponse(items=[_db_to_artifact(r) for r in rows], total=len(rows))


@app.post("/conversations/{conversation_id}/extract-artifacts", tags=["conversations"], responses={404: {"description": "Conversation not found"}})
def extract_conversation_artifacts(conversation_id: str) -> ExtractArtifactsResponse:
    """Extract artifacts from conversation trace and persist them.

    Idempotent: skips artifacts that already exist by name.
    """
    conversation_repo.get_by_id(conversation_id)
    created = message_trace_service.extract_artifacts(conversation_id)
    return ExtractArtifactsResponse(conversation_id=conversation_id, extracted=len(created), artifacts=created)


@app.get("/projects/{project_id}/artifacts", tags=["projects"], responses={404: {"description": "Project not found"}})
def list_project_artifacts(project_id: str) -> ArtifactListResponse:
    """List artifacts for a project."""
    project_repo.get_by_id(project_id)
    rows = artifact_repo.list_by_project(project_id)
    return ArtifactListResponse(items=[_db_to_artifact(r) for r in rows], total=len(rows))


@app.patch("/projects/{project_id}", tags=["projects"], responses={404: {"description": "Project not found"}})
def update_project(project_id: str, body: ProjectUpdateRequest) -> Project:
    """Update a project. Only provided fields are changed."""
    fields: dict[str, object] = {}
    if body.title is not None:
        fields["title"] = body.title
    if body.goal is not None:
        fields["goal"] = body.goal
    if body.scope is not None:
        fields["scope"] = body.scope
    if body.constraints is not None:
        fields["constraints"] = body.constraints
    if body.next_step is not None:
        fields["next_step"] = body.next_step
    if body.status is not None:
        fields["status"] = body.status.value

    if not fields:
        # No-op: just return current project
        return _db_to_project(project_repo.get_by_id(project_id))

    project_repo.update(project_id, **fields)
    return _db_to_project(project_repo.get_by_id(project_id))


# ---- Run endpoints ----


def _db_to_run(run) -> Run:
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


@app.get("/projects/{project_id}/runs", tags=["runs"], responses={404: {"description": "Project not found"}})
def list_project_runs(project_id: str) -> RunListResponse:
    """List runs for a project."""
    project_repo.get_by_id(project_id)
    rows = run_repo.list_by_project(project_id)
    return RunListResponse(items=[_db_to_run(r) for r in rows], total=len(rows))


@app.get("/conversations/{conversation_id}/runs", tags=["runs"], responses={404: {"description": "Conversation not found"}})
def list_conversation_runs(conversation_id: str) -> RunListResponse:
    """List runs for a conversation."""
    conversation_repo.get_by_id(conversation_id)
    rows = run_repo.list_by_conversation(conversation_id)
    return RunListResponse(items=[_db_to_run(r) for r in rows], total=len(rows))


@app.get("/runs/{run_id}", tags=["runs"], responses={404: {"description": "Run not found"}})
def get_run(run_id: str) -> Run:
    """Get a single run by ID."""
    run = run_repo.get_by_id(run_id)
    return _db_to_run(run)


@app.post("/runs", tags=["runs"])
def create_run(body: CreateRunRequest) -> Run:
    """Create a run record.

    Links to a conversation. If the conversation is promoted to a project,
    the run can be later linked via PATCH /runs/{run_id}.
    """
    conversation_repo.get_by_id(body.conversation_id)
    run = run_repo.create(
        conversation_id=body.conversation_id,
        goal=body.goal,
        status=body.status.value,
    )
    return _db_to_run(run)


app.include_router(conversation_router)

# ---- LLM Gateway & Provider routes ----
from swarmmind.api.llm_gateway_routes import router as gateway_router
from swarmmind.api.llm_provider_routes import router as provider_router

app.include_router(gateway_router)
app.include_router(provider_router)


# ---- Run ----

if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=API_HOST, port=API_PORT)
