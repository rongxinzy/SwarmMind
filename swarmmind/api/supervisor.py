"""Supervisor REST API — FastAPI server for human oversight."""

import logging
import os
import threading
import time
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from swarmmind.config import ACTION_TIMEOUT_SECONDS, API_HOST, API_PORT
from swarmmind.context_broker import (
    create_action_proposal,
    dispatch,
    record_supervisor_decision,
    route_to_agent,
)
from swarmmind.db import get_connection, init_db, seed_default_agents
from swarmmind.models import (
    ActionProposal,
    ApproveRequest,
    DispatchResponse,
    GoalRequest,
    PendingResponse,
    ProposalStatus,
    RejectRequest,
    StrategyChangeProposal,
    StrategyEntry,
    StrategyResponse,
    SupervisorDecision,
)
from swarmmind.renderer import render_status

logger = logging.getLogger(__name__)

# ---- Pydantic models ----

class StatusResponse(BaseModel):
    summary: str
    goal: str


class StrategyChangeApproveRequest(BaseModel):
    change_id: str


# ---- FastAPI app ----

app = FastAPI(
    title="SwarmMind Supervisor API",
    version="0.1.0",
    description="Human oversight interface for AI agent teams.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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
    # Start timeout scanner in background
    threading.Thread(target=_timeout_scanner, daemon=True).start()


# ---- Timeout scanner ----

def _timeout_scanner():
    """Background thread: find proposals pending > 5 minutes, auto-reject."""
    while True:
        time.sleep(30)
        try:
            conn = get_connection()
            try:
                cursor = conn.cursor()
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
            finally:
                conn.close()
        except Exception as e:
            logger.error("Timeout scanner error: %s", e)


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
        result = dispatch(body.goal)
        return result
    except Exception as e:
        logger.error("Dispatch error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ---- Run ----

if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=API_HOST, port=API_PORT)
