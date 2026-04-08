"""Supervisor REST API — FastAPI server for human oversight."""

import json
import logging
import threading
import time
import uuid
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from swarmmind.config import ACTION_TIMEOUT_SECONDS, API_HOST, API_PORT
from swarmmind.context_broker import (
    derive_situation_tag,
    dispatch,
    record_supervisor_decision,
)
from swarmmind.db import get_connection, health_check, init_db, seed_default_agents
from swarmmind.models import (
    ActionProposal,
    Conversation,
    ConversationListResponse,
    ConversationMode,
    ConversationRuntimeOptions,
    GoalRequest,
    MemoryContext,
    Message,
    MessageListResponse,
    PendingResponse,
    ProposalStatus,
    RejectRequest,
    RuntimeModelCatalogResponse,
    RuntimeModelOption,
    SendMessageRequest,
    SendMessageResponse,
    StrategyEntry,
    StrategyResponse,
    SupervisorDecision,
)
from swarmmind.renderer import render_status


# Deferred import for deer-flow title generation (avoid circular imports)
def _generate_title_with_deerflow(user_msg: str, assistant_msg: str) -> tuple[str, str]:
    """Generate title in isolated session using deer-flow's capabilities.

    This replicates TitleMiddleware's logic but executes in a separate thread/session,
    preventing title generation from appearing in the main conversation stream.
    """
    try:
        from deerflow.config.title_config import get_title_config
        from deerflow.models import create_chat_model
    except ImportError:
        # Fallback to simple truncation if deerflow not available
        title = user_msg[:50] if len(user_msg) <= 50 else user_msg[:47] + "..."
        return title or "New Conversation", "fallback"

    config = get_title_config()

    # Normalize content (same as TitleMiddleware._normalize_content)
    def _normalize(content: object) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [_normalize(item) for item in content]
            return "\n".join(part for part in parts if part)
        if isinstance(content, dict):
            text_value = content.get("text")
            if isinstance(text_value, str):
                return text_value
            nested = content.get("content")
            if nested is not None:
                return _normalize(nested)
        return ""

    user_normalized = _normalize(user_msg)[:500]
    assistant_normalized = _normalize(assistant_msg)[:500]

    # Build prompt using deer-flow's template
    prompt = config.prompt_template.format(
        max_words=config.max_words,
        user_msg=user_normalized,
        assistant_msg=assistant_normalized,
    )

    # Create model with thinking disabled (title doesn't need reasoning)
    model = create_chat_model(name=config.model_name, thinking_enabled=False)

    try:
        # Execute in isolated session (no thread state pollution)
        response = model.invoke(prompt)

        # Parse title (same as TitleMiddleware._parse_title)
        title_content = _normalize(response.content).strip().strip('"').strip("'")
        title = title_content[: config.max_chars] if len(title_content) > config.max_chars else title_content

        if title:
            return title, "llm"
    except Exception:
        logger.exception("Title generation failed, using fallback")

    # Fallback to truncated user message
    fallback_chars = min(config.max_chars, 50)
    if len(user_normalized) > fallback_chars:
        return user_normalized[:fallback_chars].rstrip() + "...", "fallback"
    return user_normalized or "New Conversation", "fallback"


from swarmmind.agents.general_agent import DeerFlowRuntimeAdapter
from swarmmind.runtime import (
    RuntimeConfigError,
    RuntimeExecutionError,
    RuntimeUnavailableError,
    ensure_default_runtime_instance,
)
from swarmmind.runtime.catalog import (
    ANONYMOUS_SUBJECT_ID,
    ANONYMOUS_SUBJECT_TYPE,
    list_models_for_subject,
    resolve_model_for_subject,
    sync_env_runtime_model,
)

logger = logging.getLogger(__name__)

NEW_CONVERSATION_TITLE = "New Conversation"

MODE_RUNTIME_MAP: dict[ConversationMode, dict[str, bool]] = {
    ConversationMode.FLASH: {
        "thinking_enabled": False,
        "plan_mode": False,
        "subagent_enabled": False,
    },
    ConversationMode.THINKING: {
        "thinking_enabled": True,
        "plan_mode": False,
        "subagent_enabled": False,
    },
    ConversationMode.PRO: {
        "thinking_enabled": True,
        "plan_mode": True,
        "subagent_enabled": False,
    },
    ConversationMode.ULTRA: {
        "thinking_enabled": True,
        "plan_mode": True,
        "subagent_enabled": True,
    },
}

# ---- Pydantic models ----


class StatusResponse(BaseModel):
    """Status response with summary and goal."""

    summary: str
    goal: str


class StrategyChangeApproveRequest(BaseModel):
    """Request to approve a strategy change."""

    change_id: str


# ---- FastAPI app ----

app = FastAPI(
    title="SwarmMind Supervisor API",
    version="0.1.0",
    description="Human oversight interface for AI agent teams.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    """Initialize DB on startup."""
    init_db()
    seed_default_agents()
    sync_env_runtime_model()
    ensure_default_runtime_instance()
    logger.info("SwarmMind API started on %s:%s", API_HOST, API_PORT)
    # Start cleanup scanner (proposals + expired memory) in background
    threading.Thread(target=_cleanup_scanner, daemon=True).start()


# ---- Timeout scanner ----


def _cleanup_scanner():
    """Background thread: clean up stale proposals and expired memory entries."""
    while True:
        time.sleep(30)
        try:
            conn = get_connection()
            try:
                cursor = conn.cursor()

                # 1. Auto-reject proposals pending beyond ACTION_TIMEOUT_SECONDS
                # nosec: B608 - safe, ACTION_TIMEOUT_SECONDS is a constant, not user input
                cursor.execute(
                    f"""
                    SELECT id, agent_id, description, created_at
                    FROM action_proposals
                    WHERE status = 'pending'
                    AND datetime(created_at) < datetime('now', '-{ACTION_TIMEOUT_SECONDS} seconds')
                    """,
                )
                stale = cursor.fetchall()
                for row in stale:
                    logger.info(
                        "Auto-rejecting stale proposal: id=%s (created=%s)",
                        row["id"],
                        row["created_at"],
                    )
                    cursor.execute(
                        "UPDATE action_proposals SET status = ? WHERE id = ?",
                        (ProposalStatus.REJECTED.value, row["id"]),
                    )
                    record_supervisor_decision(row["id"], SupervisorDecision.TIMEOUT)
                if stale:
                    conn.commit()

                # 2. Delete expired memory entries (TTL elapsed)
                cursor.execute(
                    """
                    DELETE FROM memory_entries
                    WHERE ttl IS NOT NULL
                    AND (strftime('%s', 'now') - strftime('%s', created_at)) > ttl
                    """,
                )
                deleted_memory = cursor.rowcount
                if deleted_memory > 0:
                    logger.info("Cleaned up %d expired memory entries.", deleted_memory)
                    conn.commit()

            finally:
                conn.close()
        except Exception as e:
            logger.error("Cleanup scanner error: %s", e)


# ---- Supervisor endpoints ----


@app.get("/pending")
def get_pending(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)) -> PendingResponse:
    """List pending action proposals (paginated)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM action_proposals WHERE status = 'pending'")
        total = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT * FROM action_proposals WHERE status = 'pending' ORDER BY created_at ASC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = cursor.fetchall()

        items = [ActionProposal(**dict(row)) for row in rows]
        return PendingResponse(items=items, total=total)
    finally:
        conn.close()


@app.post("/approve/{proposal_id}")
def approve(proposal_id: str) -> ActionProposal:
    """Approve an action proposal."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE action_proposals SET status = ? WHERE id = ? AND status = 'pending'",
            (ProposalStatus.APPROVED.value, proposal_id),
        )
        if cursor.rowcount == 0:
            # Check if it exists at all
            cursor.execute("SELECT status FROM action_proposals WHERE id = ?", (proposal_id,))
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Proposal not found")
            raise HTTPException(
                status_code=409,
                detail=f"Proposal already in status: {row['status']}",
            )
        conn.commit()
        record_supervisor_decision(proposal_id, SupervisorDecision.APPROVED)
        logger.info("Proposal %s approved by supervisor", proposal_id)
        return {"status": "approved", "id": proposal_id}
    finally:
        conn.close()


@app.post("/reject/{proposal_id}")
def reject(proposal_id: str, body: RejectRequest | None = None):
    """Reject an action proposal."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE action_proposals SET status = ? WHERE id = ? AND status = 'pending'",
            (ProposalStatus.REJECTED.value, proposal_id),
        )
        if cursor.rowcount == 0:
            cursor.execute("SELECT status FROM action_proposals WHERE id = ?", (proposal_id,))
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Proposal not found")
            raise HTTPException(
                status_code=409,
                detail=f"Proposal already in status: {row['status']}",
            )
        conn.commit()
        record_supervisor_decision(proposal_id, SupervisorDecision.REJECTED)
        logger.info("Proposal %s rejected by supervisor", proposal_id)
        reason = body.reason if body else None
        return {"status": "rejected", "id": proposal_id, "reason": reason}
    finally:
        conn.close()


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
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT situation_tag, agent_id, success_count, failure_count FROM strategy_table ORDER BY situation_tag"
        )
        rows = cursor.fetchall()
        entries = [
            StrategyEntry(
                situation_tag=row["situation_tag"],
                agent_id=row["agent_id"],
                success_count=row["success_count"],
                failure_count=row["failure_count"],
            )
            for row in rows
        ]
        return StrategyResponse(entries=entries)
    finally:
        conn.close()


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
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


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


def _row_to_conversation(row) -> Conversation:
    return Conversation(
        id=row["id"],
        title=row["title"],
        title_status=row["title_status"],
        title_source=row["title_source"],
        title_generated_at=(str(row["title_generated_at"]) if row["title_generated_at"] is not None else None),
        runtime_profile_id=(str(row["runtime_profile_id"]) if row["runtime_profile_id"] is not None else None),
        runtime_instance_id=(str(row["runtime_instance_id"]) if row["runtime_instance_id"] is not None else None),
        thread_id=str(row["thread_id"]) if row["thread_id"] is not None else None,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _serialize_stream_event(event_type: str, **payload) -> str:
    return json.dumps({"type": event_type, **payload}, ensure_ascii=False) + "\n"


def _tool_activity_label(tool_name: str, args: dict | None = None) -> str:
    args = args or {}

    if tool_name == "search":
        query = args.get("query")
        if isinstance(query, str) and query.strip():
            return f"检索资料：{query.strip()[:60]}"
        return "检索外部资料"
    if tool_name == "crawl":
        return "抓取网页内容"
    if tool_name == "fetch":
        return "获取远端内容"
    if tool_name == "view_image":
        return "查看图像资料"
    if tool_name == "read_file":
        return "读取文件"
    if tool_name == "write_file":
        return "写入文件"
    if tool_name == "edit_file":
        return "编辑文件"
    if tool_name == "bash":
        return "执行命令"
    if tool_name == "present_files":
        return "整理输出产物"
    if tool_name == "ask_clarification":
        return "请求补充信息"
    if tool_name == "tool_search":
        return "搜索可用工具"

    return f"执行工具：{tool_name}"


def _task_card_title(tool_args: dict | None) -> str:
    if not isinstance(tool_args, dict):
        return "新的协作分工"

    description = tool_args.get("description")
    if isinstance(description, str) and description.strip():
        return description.strip()

    prompt = tool_args.get("prompt")
    if isinstance(prompt, str) and prompt.strip():
        return prompt.strip().splitlines()[0][:80]

    return "新的协作分工"


def _task_status_from_result(content: str) -> tuple[str, str | None]:
    normalized = content.strip()
    if normalized.startswith("Task Succeeded. Result:"):
        return "completed", normalized.split("Task Succeeded. Result:", 1)[1].strip() or None
    if normalized.startswith("Task failed."):
        return "failed", normalized.split("Task failed.", 1)[1].strip() or None
    if normalized.startswith("Task timed out"):
        return "failed", normalized
    return "running", normalized or None


def _persist_user_message(conversation_id: str, content: str) -> Message:
    user_msg_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM conversations WHERE id = ?", (conversation_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

        cursor.execute(
            "INSERT INTO messages (id, conversation_id, role, content) VALUES (?, ?, ?, ?)",
            (user_msg_id, conversation_id, "user", content),
        )
        cursor.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )
        conn.commit()

        cursor.execute("SELECT * FROM messages WHERE id = ?", (user_msg_id,))
        row = cursor.fetchone()
        return Message(
            id=str(row["id"]),
            conversation_id=str(row["conversation_id"]),
            role=str(row["role"]),
            content=str(row["content"]),
            created_at=str(row["created_at"]),
        )
    finally:
        conn.close()


def _persist_assistant_message(conversation_id: str, content: str) -> Message:
    assistant_msg_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (id, conversation_id, role, content) VALUES (?, ?, ?, ?)",
            (assistant_msg_id, conversation_id, "assistant", content),
        )
        cursor.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )
        conn.commit()

        cursor.execute("SELECT * FROM messages WHERE id = ?", (assistant_msg_id,))
        row = cursor.fetchone()
        return Message(
            id=str(row["id"]),
            conversation_id=str(row["conversation_id"]),
            role=str(row["role"]),
            content=str(row["content"]),
            created_at=str(row["created_at"]),
        )
    finally:
        conn.close()


def _normalize_model_name(model_name: str | None) -> str | None:
    if model_name is None:
        return None

    value = model_name.strip()
    return value or None


def _resolve_model_name_for_request(model_name: str | None) -> str:
    normalized_model_name = _normalize_model_name(model_name)
    try:
        selected_model = resolve_model_for_subject(
            requested_model_name=normalized_model_name,
            subject_type=ANONYMOUS_SUBJECT_TYPE,
            subject_id=ANONYMOUS_SUBJECT_ID,
        )
    except RuntimeConfigError as exc:
        raise HTTPException(
            status_code=400 if normalized_model_name else 503,
            detail=str(exc),
        ) from exc
    return selected_model.name


def _conversation_thread_id(conversation_id: str) -> str:
    return conversation_id


def _bind_conversation_runtime(conversation_id: str) -> tuple[object, str]:
    runtime_instance = ensure_default_runtime_instance()
    thread_id = _conversation_thread_id(conversation_id)

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE conversations
            SET runtime_profile_id = ?, runtime_instance_id = ?, thread_id = ?
            WHERE id = ?
            """,
            (
                runtime_instance.runtime_profile_id,
                runtime_instance.runtime_instance_id,
                thread_id,
                conversation_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return runtime_instance, thread_id


def _format_runtime_error(exc: Exception) -> str:
    if isinstance(exc, (RuntimeConfigError, RuntimeUnavailableError, RuntimeExecutionError)):
        return f"DeerFlow Runtime error: {exc}"
    return f"Unexpected DeerFlow execution error: {exc}"


def _resolve_runtime_options(body: SendMessageRequest) -> ConversationRuntimeOptions:
    effective_mode = body.mode
    logger.info(
        "[DEBUG] _resolve_runtime_options: body.mode=%s, effective_mode=%s",
        body.mode,
        effective_mode,
    )
    if effective_mode is None:
        effective_mode = ConversationMode.THINKING if body.reasoning else ConversationMode.FLASH

    runtime_flags = MODE_RUNTIME_MAP[effective_mode]
    logger.info("[DEBUG] _resolve_runtime_options: runtime_flags=%s", runtime_flags)
    options = ConversationRuntimeOptions(
        mode=effective_mode,
        model_name=_resolve_model_name_for_request(body.model_name),
        thinking_enabled=runtime_flags["thinking_enabled"],
        plan_mode=runtime_flags["plan_mode"],
        subagent_enabled=runtime_flags["subagent_enabled"],
    )
    logger.info(
        "[DEBUG] _resolve_runtime_options: returning options with subagent_enabled=%s",
        options.subagent_enabled,
    )
    return options


def _general_agent_status_labels(runtime_options: ConversationRuntimeOptions) -> tuple[str, str]:
    if runtime_options.mode == ConversationMode.ULTRA:
        return (
            "Agent Team 正在判断这轮探索需要怎样的协作方式",
            "Agent Team 正在协作处理你的问题",
        )
    if runtime_options.mode == ConversationMode.PRO:
        return (
            "正在规划这轮任务的执行方式",
            "正在按规划生成结果",
        )
    if runtime_options.mode == ConversationMode.THINKING:
        return (
            "正在分析你的问题",
            "正在整理深入回复",
        )
    return (
        "正在准备快速回复",
        "正在快速生成结果",
    )


def _translate_general_agent_event(
    event: dict,
    runtime_options: ConversationRuntimeOptions,
) -> list[str]:
    event_type = event.get("type")

    if event_type == "assistant_reasoning":
        if not runtime_options.thinking_enabled:
            return []
        content = event.get("content")
        if isinstance(content, str) and content.strip():
            return [
                _serialize_stream_event(
                    "thinking",
                    message_id=event.get("message_id"),
                    content=content,
                ),
            ]
        return []

    if event_type == "assistant_message":
        content = event.get("content")
        if isinstance(content, str) and content:
            return [
                _serialize_stream_event(
                    "assistant_message",
                    message_id=event.get("message_id"),
                    content=content,
                ),
            ]
        return []

    if event_type == "assistant_tool_calls":
        if not runtime_options.subagent_enabled:
            return []
        tool_calls = event.get("tool_calls")
        if not isinstance(tool_calls, list):
            return []

        lines: list[str] = []
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue

            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args", {})
            tool_call_id = tool_call.get("id")

            if tool_name == "task":
                lines.append(
                    _serialize_stream_event(
                        "team_task",
                        task={
                            "id": tool_call_id,
                            "title": _task_card_title(tool_args if isinstance(tool_args, dict) else {}),
                            "status": "running",
                            "detail": "Agent Team 正在协同处理这个子任务。",
                        },
                    ),
                )
                continue

            lines.append(
                _serialize_stream_event(
                    "team_activity",
                    activity={
                        "id": tool_call_id or str(uuid.uuid4()),
                        "tool_name": tool_name,
                        "label": _tool_activity_label(
                            str(tool_name),
                            tool_args if isinstance(tool_args, dict) else {},
                        ),
                        "status": "running",
                    },
                ),
            )
        return lines

    if event_type == "tool_result":
        tool_name = str(event.get("tool_name") or "unknown")
        tool_call_id = event.get("tool_call_id")
        content = str(event.get("content") or "").strip()

        # Handle ask_clarification tool (available in all modes, not just subagent mode)
        if tool_name == "ask_clarification":
            return [
                _serialize_stream_event(
                    "clarification_request",
                    clarification={
                        "id": tool_call_id,
                        "content": content,
                    },
                ),
            ]

        if not runtime_options.subagent_enabled:
            return []

        if tool_name == "task":
            status, detail = _task_status_from_result(content)
            return [
                _serialize_stream_event(
                    "team_task",
                    task={
                        "id": tool_call_id,
                        "status": status,
                        "detail": detail,
                    },
                ),
            ]

        return [
            _serialize_stream_event(
                "team_activity",
                activity={
                    "id": tool_call_id or str(uuid.uuid4()),
                    "tool_name": tool_name,
                    "label": _tool_activity_label(tool_name),
                    "status": "completed",
                    "detail": content[:240] if content else None,
                },
            ),
        ]

    # Handle custom events from task_tool (task_started, task_running, task_completed, task_failed)
    if event_type == "custom_event":
        if not runtime_options.subagent_enabled:
            return []

        custom_event_type = event.get("event_type")
        task_id = event.get("task_id")

        if custom_event_type == "task_started":
            return [
                _serialize_stream_event(
                    "task_started",
                    task={
                        "id": task_id,
                        "description": event.get("description"),
                        "status": "in_progress",
                    },
                ),
            ]

        if custom_event_type == "task_running":
            return [
                _serialize_stream_event(
                    "task_running",
                    task={
                        "id": task_id,
                        "message": event.get("message"),
                    },
                ),
            ]

        if custom_event_type == "task_completed":
            return [
                _serialize_stream_event(
                    "task_completed",
                    task={
                        "id": task_id,
                        "result": event.get("result"),
                        "status": "completed",
                    },
                ),
            ]

        if custom_event_type == "task_failed":
            return [
                _serialize_stream_event(
                    "task_failed",
                    task={
                        "id": task_id,
                        "error": event.get("error"),
                        "status": "failed",
                    },
                ),
            ]

    return []


def _maybe_generate_conversation_title(conversation_id: str) -> None:
    """Generate a conversation title after the first complete exchange.

    Uses deer-flow's title generation capabilities in an isolated session,
    preventing title LLM calls from polluting the main conversation stream.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, title_status
            FROM conversations
            WHERE id = ?
            """,
            (conversation_id,),
        )
        conversation = cursor.fetchone()
        if conversation is None or conversation["title_status"] != "pending":
            return

        cursor.execute(
            """
            SELECT role, content
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (conversation_id,),
        )
        rows = cursor.fetchall()
        user_messages = [row["content"] for row in rows if row["role"] == "user"]
        assistant_messages = [row["content"] for row in rows if row["role"] == "assistant"]

        if len(user_messages) != 1 or len(assistant_messages) < 1:
            return

        # Generate title in isolated session using deer-flow capabilities
        title, source = _generate_title_with_deerflow(
            user_messages[0],
            assistant_messages[0],
        )

        cursor.execute(
            """
            UPDATE conversations
            SET
                title = ?,
                title_status = ?,
                title_source = ?,
                title_generated_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND title_status = 'pending'
            """,
            (
                title or NEW_CONVERSATION_TITLE,
                "generated" if source == "llm" else "fallback",
                source,
                conversation_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


@app.get("/conversations")
def list_conversations() -> ConversationListResponse:
    """List all conversations ordered by updated_at descending."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM conversations")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT * FROM conversations ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        items = [_row_to_conversation(row) for row in rows]
        return ConversationListResponse(items=items, total=total)
    finally:
        conn.close()


@app.post("/conversations")
def create_conversation(body: GoalRequest) -> Conversation:
    """Create a new conversation with the first user message."""
    conv_id = str(uuid.uuid4())

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO conversations (id, title, title_status)
            VALUES (?, ?, ?)
            """,
            (conv_id, NEW_CONVERSATION_TITLE, "pending"),
        )
        conn.commit()

        cursor.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,))
        row = cursor.fetchone()
        return _row_to_conversation(row)
    finally:
        conn.close()


@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str) -> Conversation:
    """Get a single conversation by ID."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return _row_to_conversation(row)
    finally:
        conn.close()


@app.get("/conversations/{conversation_id}/messages")
def get_conversation_messages(conversation_id: str) -> MessageListResponse:
    """Get all messages for a conversation."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM conversations WHERE id = ?", (conversation_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

        cursor.execute(
            "SELECT COUNT(*) as total FROM messages WHERE conversation_id = ?",
            (conversation_id,),
        )
        total = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,),
        )
        rows = cursor.fetchall()
        items = [
            Message(
                id=str(row["id"]),
                conversation_id=str(row["conversation_id"]),
                role=str(row["role"]),
                content=str(row["content"]),
                created_at=str(row["created_at"]),
            )
            for row in rows
        ]
        return MessageListResponse(items=items, total=total)
    finally:
        conn.close()


@app.post("/conversations/{conversation_id}/messages", include_in_schema=False)
def send_message(conversation_id: str, body: SendMessageRequest):
    """Internal compatibility endpoint for non-streaming conversation turns.

    All execution flows through the single DeerFlow Runtime Instance.
    """
    # Save user message (validates conversation exists via FK or explicit check)
    user_msg_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Validate conversation exists
        cursor.execute("SELECT id FROM conversations WHERE id = ?", (conversation_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        # Insert user message
        cursor.execute(
            "INSERT INTO messages (id, conversation_id, role, content) VALUES (?, ?, ?, ?)",
            (user_msg_id, conversation_id, "user", body.content),
        )
        cursor.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )
        conn.commit()
    finally:
        conn.close()

    # Build MemoryContext using conversation_id as session_id
    memory_ctx = MemoryContext(
        user_id="supervisor",
        session_id=conversation_id,
    )
    runtime_options = _resolve_runtime_options(body)
    situation_tag = derive_situation_tag(body.content)

    dispatch_result = dispatch(
        body.content,
        user_id="supervisor",
        session_id=conversation_id,
        override_situation_tag=situation_tag,
    )
    proposal_id = dispatch_result.action_proposal_id

    conn2 = get_connection()
    try:
        cursor2 = conn2.cursor()
        cursor2.execute(
            "UPDATE action_proposals SET status = ? WHERE id = ?",
            (ProposalStatus.APPROVED.value, proposal_id),
        )
        conn2.commit()
    finally:
        conn2.close()
    record_supervisor_decision(proposal_id, SupervisorDecision.APPROVED)

    try:
        runtime_instance, _thread_id = _bind_conversation_runtime(conversation_id)
        runtime_adapter = DeerFlowRuntimeAdapter(
            runtime_instance=runtime_instance,
            default_model=runtime_options.model_name,
            thinking_enabled=runtime_options.thinking_enabled,
            subagent_enabled=runtime_options.subagent_enabled,
            plan_mode=runtime_options.plan_mode,
        )
        completed_proposal = runtime_adapter.act(
            body.content,
            proposal_id,
            ctx=memory_ctx,
            runtime_options=runtime_options,
        )
        ai_response = completed_proposal.description
    except Exception as e:
        logger.error("DeerFlowRuntimeAdapter execution error: %s", e)
        ai_response = _format_runtime_error(e)

    # Save assistant response
    assistant_msg_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (id, conversation_id, role, content) VALUES (?, ?, ?, ?)",
            (assistant_msg_id, conversation_id, "assistant", ai_response),
        )
        cursor.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )
        conn.commit()
    finally:
        conn.close()

    _maybe_generate_conversation_title(conversation_id)

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE id = ?", (user_msg_id,))
        row = cursor.fetchone()
        user_msg = Message(
            id=str(row["id"]),
            conversation_id=str(row["conversation_id"]),
            role=str(row["role"]),
            content=str(row["content"]),
            created_at=str(row["created_at"]),
        )
        cursor.execute("SELECT * FROM messages WHERE id = ?", (assistant_msg_id,))
        row = cursor.fetchone()
        assistant_msg = Message(
            id=str(row["id"]),
            conversation_id=str(row["conversation_id"]),
            role=str(row["role"]),
            content=str(row["content"]),
            created_at=str(row["created_at"]),
        )

        return SendMessageResponse(
            user_message=user_msg,
            assistant_message=assistant_msg,
        )
    finally:
        conn.close()


@app.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str) -> Conversation:
    """Delete a conversation and all its messages."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM conversations WHERE id = ?", (conversation_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

        cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        conn.commit()
        return {"status": "deleted", "id": conversation_id}
    finally:
        conn.close()


# ---- Collaboration Trace Endpoints ----


@app.get("/conversations/{conversation_id}/trace")
def get_conversation_trace(conversation_id: str) -> dict:
    """获取会话的协作轨迹（回放用）。

    复用 deer-flow checkpointer 数据，零侵入设计：
    1. 从 conversations 表读取 thread_id
    2. 从 deer-flow SqliteSaver 读取 checkpoints
    3. 解析 ThreadState 转换为协作轨迹

    Args:
        conversation_id: SwarmMind conversation ID (maps to deer-flow thread_id)

    Returns:
        Collaboration trace with events, status, and summary.
    """
    # 延迟导入，避免循环依赖
    from swarmmind.services.trace_service import trace_service

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, thread_id FROM conversations WHERE id = ?", (conversation_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # 优先使用 thread_id，否则用 conversation_id 作为 fallback
        thread_id = row["thread_id"] or conversation_id
    finally:
        conn.close()

    # 从 deer-flow checkpointer 读取轨迹
    try:
        trace = trace_service.get_conversation_trace(thread_id)
        return trace
    except Exception as e:
        logger.error("Failed to get trace for thread %s: %s", thread_id, e)
        # 降级返回空轨迹，不阻断主流程
        return {
            "thread_id": thread_id,
            "status": "error",
            "events": [],
            "summary": f"读取轨迹失败: {e!s}",
            "checkpoint_count": 0,
        }


def _stream_conversation_message(conversation_id: str, body: SendMessageRequest):
    """Stream a ChatSession turn with SwarmMind runtime semantics."""
    user_message = _persist_user_message(conversation_id, body.content)
    yield _serialize_stream_event(
        "status",
        phase="accepted",
        label="消息已加入当前会话",
    )
    yield _serialize_stream_event(
        "user_message",
        message={
            "id": user_message.id,
            "role": user_message.role,
            "content": user_message.content,
            "created_at": user_message.created_at,
        },
    )

    memory_ctx = MemoryContext(
        user_id="supervisor",
        session_id=conversation_id,
    )
    runtime_options = _resolve_runtime_options(body)
    routing_label, running_label = _general_agent_status_labels(runtime_options)

    ai_response = ""
    situation_tag = derive_situation_tag(body.content)

    try:
        yield _serialize_stream_event(
            "status",
            phase="routing",
            label=routing_label,
        )

        dispatch_result = dispatch(
            body.content,
            user_id="supervisor",
            session_id=conversation_id,
            override_situation_tag=situation_tag,
        )
        proposal_id = dispatch_result.action_proposal_id

        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE action_proposals SET status = ? WHERE id = ?",
                (ProposalStatus.APPROVED.value, proposal_id),
            )
            conn.commit()
        finally:
            conn.close()
        record_supervisor_decision(proposal_id, SupervisorDecision.APPROVED)

        runtime_instance, _thread_id = _bind_conversation_runtime(conversation_id)
        runtime_adapter = DeerFlowRuntimeAdapter(
            runtime_instance=runtime_instance,
            default_model=runtime_options.model_name,
            thinking_enabled=runtime_options.thinking_enabled,
            subagent_enabled=runtime_options.subagent_enabled,
            plan_mode=runtime_options.plan_mode,
        )

        yield _serialize_stream_event(
            "status",
            phase="running",
            label=running_label,
        )

        stream = runtime_adapter.stream_events(
            body.content,
            ctx=memory_ctx,
            runtime_options=runtime_options,
        )
        event_count = 0
        while True:
            try:
                event = next(stream)
                event_count += 1
                if event_count <= 5 or event_count % 10 == 0:
                    logger.info("Stream event #%d: type=%s", event_count, event.get("type"))
            except StopIteration as stop:
                ai_response, _tool_results = stop.value
                logger.info("Stream completed: events=%d, response_length=%d", event_count, len(ai_response))
                break
            except Exception as stream_error:
                logger.error("Stream event error: %s", stream_error, exc_info=True)
                raise

            try:
                for line in _translate_general_agent_event(event, runtime_options):
                    yield line
            except Exception as translate_error:
                logger.error("Event translation error: %s, event=%s", translate_error, event)
                raise

        if not ai_response.strip():
            ai_response = "本轮运行已完成，但没有生成可展示的最终回答。"
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Conversation stream error: %s", e, exc_info=True)
        ai_response = _format_runtime_error(e)
        yield _serialize_stream_event(
            "status",
            phase="error",
            label="DeerFlow Runtime 执行失败",
        )
        yield _serialize_stream_event(
            "assistant_message",
            message_id=f"assistant-error-{uuid.uuid4()}",
            content=ai_response,
        )

    assistant_message = _persist_assistant_message(conversation_id, ai_response)
    _maybe_generate_conversation_title(conversation_id)
    conversation = get_conversation(conversation_id)

    yield _serialize_stream_event(
        "assistant_final",
        message={
            "id": assistant_message.id,
            "role": assistant_message.role,
            "content": assistant_message.content,
            "created_at": assistant_message.created_at,
        },
    )
    yield _serialize_stream_event(
        "title",
        conversation={
            "id": conversation.id,
            "title": conversation.title,
            "title_status": conversation.title_status,
            "title_source": conversation.title_source,
            "title_generated_at": conversation.title_generated_at,
            "updated_at": conversation.updated_at,
        },
    )
    yield _serialize_stream_event(
        "status",
        phase="completed",
        label="本轮会话已完成",
    )
    yield _serialize_stream_event("done")


@app.post("/conversations/{conversation_id}/messages/stream")
def send_message_stream(conversation_id: str, body: SendMessageRequest) -> StreamingResponse:
    """Stream a ChatSession turn with runtime state and final persistence."""
    # Validate before opening the streaming response so 404 is returned normally.
    get_conversation(conversation_id)
    return StreamingResponse(
        _stream_conversation_message(conversation_id, body),
        media_type="application/x-ndjson",
    )


class ClarificationResponseRequest(BaseModel):
    """Request to respond to a clarification prompt."""

    tool_call_id: str
    response: str


@app.post("/conversations/{conversation_id}/clarification")
def respond_to_clarification(conversation_id: str, body: ClarificationResponseRequest) -> dict:
    """Respond to a clarification request from the AI.

    This endpoint is called when the user responds to an ask_clarification tool call.
    The response is added as a ToolMessage to the conversation history, and the
    conversation is resumed.
    """
    # Validate conversation exists
    get_conversation(conversation_id)

    # Persist the clarification response as a user message with tool_call_id
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.now(UTC).isoformat()
        message_id = str(uuid.uuid4())

        # Store as a special message that will be treated as a tool response
        cursor.execute(
            """
            INSERT INTO messages (id, conversation_id, role, content, created_at, tool_call_id, name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                conversation_id,
                "tool",
                body.response,
                now,
                body.tool_call_id,
                "ask_clarification_response",
            ),
        )
        conn.commit()

        return {
            "id": message_id,
            "role": "tool",
            "content": body.response,
            "tool_call_id": body.tool_call_id,
            "created_at": now,
        }
    finally:
        conn.close()


# ---- Run ----

if __name__ == "__main__":
    import uvicorn

    # Initialize database on startup
    logger.info("Initializing SwarmMind database...")
    init_db()
    health = health_check()
    if health["status"] == "healed":
        logger.info("Database healed and initialized with new schema.")
    else:
        logger.info("Database health check passed.")

    # Seed default agents if needed
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM agents WHERE agent_id = 'general'")
        count = cursor.fetchone()[0]
        if count == 0:
            logger.info("Seeding default agents...")
            seed_default_agents()
        else:
            logger.info("Default agents already exist.")
    finally:
        conn.close()

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=API_HOST, port=API_PORT)
