"""Supervisor REST API — FastAPI server for human oversight."""

import asyncio
import logging
import os
import threading
import time
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from swarmmind.config import ACTION_TIMEOUT_SECONDS, API_HOST, API_PORT, DEER_FLOW_CONFIG_PATH
from swarmmind.context_broker import (
    derive_situation_tag,
    dispatch,
    record_supervisor_decision,
    route_to_agent,
)
from swarmmind.db import get_connection, init_db, seed_default_agents
from swarmmind.models import (
    ActionProposal,
    ApproveRequest,
    Conversation,
    ConversationListResponse,
    DispatchResponse,
    GoalRequest,
    MemoryContext,
    Message,
    MessageListResponse,
    PendingResponse,
    ProposalStatus,
    RejectRequest,
    SendMessageRequest,
    SendMessageResponse,
    StrategyChangeProposal,
    StrategyEntry,
    StrategyResponse,
    SupervisorDecision,
)
from swarmmind.renderer import generate_conversation_title_from_exchange, render_status
from swarmmind.llm import LLMClient, LLMError
from swarmmind.agents.finance import FinanceAgent
from swarmmind.agents.code_review import CodeReviewAgent
from swarmmind.agents.general_agent import GeneralAgent

logger = logging.getLogger(__name__)

NEW_CONVERSATION_TITLE = "New Conversation"

# ---- Pydantic models ----

class StatusResponse(BaseModel):
    summary: str
    goal: str


class StrategyChangeApproveRequest(BaseModel):
    change_id: str


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=2000)
    reasoning: bool = False  # Whether to enable LLM reasoning/thinking mode
    history: list[dict] = Field(default=[], exclude=True)  # reserved for Phase 2


class ChatResponse(BaseModel):
    response: str


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
def startup():
    """Initialize DB on startup."""
    init_db()
    seed_default_agents()
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
                        row["id"], row["created_at"],
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
def get_pending(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    """List pending action proposals (paginated)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) as total FROM action_proposals WHERE status = 'pending'"
        )
        total = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT * FROM action_proposals WHERE status = 'pending' "
            "ORDER BY created_at ASC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = cursor.fetchall()

        items = [ActionProposal(**dict(row)) for row in rows]
        return PendingResponse(items=items, total=total)
    finally:
        conn.close()


@app.post("/approve/{proposal_id}")
def approve(proposal_id: str):
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
def reject(proposal_id: str, body: Optional[RejectRequest] = None):
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
    """
    LLM Status Renderer: given a goal, read shared context and
    generate a human-readable status summary (Phase 1: prose only).
    """
    try:
        summary = render_status(goal)
        return StatusResponse(summary=summary, goal=goal)
    except Exception as e:
        logger.error("Status renderer error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/strategy")
def get_strategy():
    """View the strategy routing table."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT situation_tag, agent_id, success_count, failure_count "
            "FROM strategy_table ORDER BY situation_tag"
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
def health():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ---- Conversation endpoints ----

def _row_to_conversation(row) -> Conversation:
    return Conversation(
        id=row["id"],
        title=row["title"],
        title_status=row["title_status"],
        title_source=row["title_source"],
        title_generated_at=(
            str(row["title_generated_at"]) if row["title_generated_at"] is not None else None
        ),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _maybe_generate_conversation_title(conversation_id: str) -> None:
    """
    Generate a conversation title after the first complete exchange.

    This mirrors deer-flow's timing: wait until the first assistant response is
    present, then persist the title into conversation metadata exactly once.
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
        assistant_messages = [
            row["content"] for row in rows if row["role"] == "assistant"
        ]

        if len(user_messages) != 1 or len(assistant_messages) < 1:
            return

        title, source = generate_conversation_title_from_exchange(
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
def list_conversations():
    """List all conversations ordered by updated_at descending."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM conversations")
        total = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC"
        )
        rows = cursor.fetchall()
        items = [_row_to_conversation(row) for row in rows]
        return ConversationListResponse(items=items, total=total)
    finally:
        conn.close()


@app.post("/conversations")
def create_conversation(body: GoalRequest):
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
def get_conversation(conversation_id: str):
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
def get_conversation_messages(conversation_id: str):
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
        items = [Message(id=str(row["id"]), conversation_id=str(row["conversation_id"]), role=str(row["role"]), content=str(row["content"]), created_at=str(row["created_at"])) for row in rows]
        return MessageListResponse(items=items, total=total)
    finally:
        conn.close()


@app.post("/conversations/{conversation_id}/messages")
def send_message(conversation_id: str, body: SendMessageRequest):
    """
    Send a user message and get an AI response.

    Routing logic:
    1. Try dispatch() to route to a specialized agent
    2. If routed: auto-approve, execute agent, use result as response
    3. If no_route: fall back to render_status() (direct LLM)
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

    # Route through ContextBroker — use lightweight check first to avoid creating orphaned proposals
    situation_tag = derive_situation_tag(body.content)
    routed_agent_id = route_to_agent(situation_tag)

    if routed_agent_id is None:
        # No specialized agent matched — use GeneralAgent via dispatch (consistent flow)
        try:
            general_agent = GeneralAgent(
                deer_flow_config_path=DEER_FLOW_CONFIG_PATH,
            )
            # Use dispatch() with override to get a proper pending proposal routed to GeneralAgent
            dispatch_result = dispatch(
                body.content,
                user_id="supervisor",
                session_id=conversation_id,
                override_situation_tag="general",
            )
            proposal_id = dispatch_result.action_proposal_id

            # Auto-approve the proposal (supervisor decision)
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

            # Execute with GeneralAgent
            completed_proposal = general_agent.act(
                body.content, proposal_id, ctx=memory_ctx
            )
            ai_response = completed_proposal.description
        except Exception as e:
            logger.error("GeneralAgent error: %s", e)
            ai_response = f"I attempted to process your request using the general agent but encountered an error: {e}"
    else:
        # Agent matched — full dispatch, auto-approve, and execute
        dispatch_result = dispatch(
            body.content,
            user_id="supervisor",
            session_id=conversation_id,
        )
        proposal_id = dispatch_result.action_proposal_id
        agent_id = dispatch_result.agent_id

        # Mark proposal as approved
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

        # Log supervisor decision
        record_supervisor_decision(proposal_id, SupervisorDecision.APPROVED)

        # Execute the agent with MemoryContext
        try:
            if agent_id == "finance":
                agent = FinanceAgent()
            elif agent_id == "code_review":
                agent = CodeReviewAgent()
            else:
                # Fallback: use GeneralAgent (DeerFlow)
                agent = GeneralAgent(deer_flow_config_path=DEER_FLOW_CONFIG_PATH)

            completed_proposal = agent.act(body.content, proposal_id, ctx=memory_ctx)
            ai_response = completed_proposal.description
        except Exception as e:
            logger.error("Agent execution error: %s", e)
            ai_response = f"I attempted to process your request but encountered an error: {e}"

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
        user_msg = Message(id=str(row["id"]), conversation_id=str(row["conversation_id"]), role=str(row["role"]), content=str(row["content"]), created_at=str(row["created_at"]))
        cursor.execute("SELECT * FROM messages WHERE id = ?", (assistant_msg_id,))
        row = cursor.fetchone()
        assistant_msg = Message(id=str(row["id"]), conversation_id=str(row["conversation_id"]), role=str(row["role"]), content=str(row["content"]), created_at=str(row["created_at"]))

        return SendMessageResponse(
            user_message=user_msg,
            assistant_message=assistant_msg,
        )
    finally:
        conn.close()


@app.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
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


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint — Phase 1 uses render_status() for stateless LLM queries.
    Does not create proposals or invoke agents (reserved for Phase 2).
    """
    try:
        # Run blocking LLM call in thread pool to avoid blocking the event loop
        enhanced_message = (
            f"[respond_in_language] Detect the language of the text below "
            f"and respond in that same language.\nText: {request.message}\n"
        )
        summary = await asyncio.to_thread(render_status, enhanced_message, request.reasoning)
        return ChatResponse(response=summary)
    except Exception as e:
        logger.error("Chat error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


async def _stream_chat(request: ChatRequest):
    """Async generator for streaming chat responses in data-stream format."""
    import json

    enhanced_message = (
        f"[respond_in_language] Detect the language of the text below "
        f"and respond in that same language.\nText: {request.message}\n"
    )
    messages = [{"role": "user", "content": enhanced_message}]
    try:
        client = LLMClient()
    except LLMError as e:
        yield f"3:{json.dumps(str(e))}\n"
        return

    try:
        async for chunk in client.stream(messages, max_tokens=1024, reasoning=request.reasoning):
            if "error" in chunk:
                yield f"3:{json.dumps(chunk['error'])}\n"
                return
            if chunk.get("thinking"):
                # data-stream thinking delta: "1:{text}\n"
                yield f"1:{json.dumps(chunk['thinking'])}\n"
            if chunk.get("text"):
                # data-stream text delta: "0:{text}\n"
                yield f"0:{json.dumps(chunk['text'])}\n"
            if chunk.get("finish"):
                # data-stream message finish: "d:{finishReason, usage}\n"
                yield f"d:{json.dumps({'finishReason': chunk['finish'], 'usage': {}})}\n"
    except Exception as e:
        logger.error("Chat stream error: %s", e)
        yield f"3:{json.dumps(str(e))}\n"


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint — returns SSE in data-stream format for assistant-ui.

    Format:
      0:{text}   — text delta (JSON string)
      d:{finish} — message finish (JSON {finishReason, usage})
      3:{error}  — error message (JSON string)
    """
    return StreamingResponse(
        _stream_chat(request),
        media_type="text/plain; charset=utf-8",
        headers={"x-vercel-ai-data-stream": "v1"},
    )


# ---- Run ----

if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=API_HOST, port=API_PORT)
