"""Pydantic models for SwarmMind Phase 1."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    ERROR = "error"


class ProposalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


class SupervisorDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class Agent(BaseModel):
    agent_id: str
    domain: str
    system_prompt: str
    created_at: datetime


class WorkingMemoryEntry(BaseModel):
    key: str
    value: str
    domain_tags: Optional[str] = None
    last_writer_agent_id: Optional[str] = None
    updated_at: datetime


class StrategyEntry(BaseModel):
    situation_tag: str
    agent_id: str
    success_count: int = 0
    failure_count: int = 0


class ActionProposal(BaseModel):
    id: str
    agent_id: str
    description: str
    target_resource: Optional[str] = None
    preconditions: Optional[dict] = None
    postconditions: Optional[dict] = None
    confidence: float = 0.5
    status: ProposalStatus = ProposalStatus.PENDING
    created_at: datetime


class StrategyChangeProposal(BaseModel):
    id: str
    situation_tag: str
    proposed_agent_id: str
    reason: Optional[str] = None
    status: ProposalStatus = ProposalStatus.PENDING
    proposed_at: datetime


class EventLogEntry(BaseModel):
    id: Optional[int] = None
    timestamp: datetime
    goal: str
    situation_tag: Optional[str] = None
    dispatched_agent_id: Optional[str] = None
    action_proposal_id: Optional[str] = None
    supervisor_decision: Optional[SupervisorDecision] = None
    outcome: Optional[str] = None
    latency_ms: Optional[int] = None


# ---- API Request/Response models ----

class GoalRequest(BaseModel):
    goal: str = Field(..., max_length=2000)


class ApproveRequest(BaseModel):
    id: str


class RejectRequest(BaseModel):
    id: str
    reason: Optional[str] = None


class DispatchResponse(BaseModel):
    action_proposal_id: str
    agent_id: str
    status: str


class PendingResponse(BaseModel):
    items: list[ActionProposal]
    total: int


class StatusResponse(BaseModel):
    summary: str  # LLM-generated prose summary
    goal: str


class StrategyResponse(BaseModel):
    entries: list[StrategyEntry]
