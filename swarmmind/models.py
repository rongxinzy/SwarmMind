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


# ---- Layered Memory models ----

class MemoryLayer(str, Enum):
    USER_SOUL = "L4_user_soul"
    PROJECT = "L3_project"
    TEAM = "L2_team"
    TMP = "L1_tmp"


class MemoryScope(BaseModel):
    layer: MemoryLayer
    scope_id: str


class MemoryEntry(BaseModel):
    id: str
    scope: MemoryScope
    key: str
    value: str
    tags: list[str] = []
    created_at: datetime
    updated_at: datetime
    ttl: int | None = None
    version: int = 1
    last_writer_agent_id: str | None = None


class MemoryContext(BaseModel):
    """Carries scope information through a request lifecycle."""
    user_id: str
    project_id: str | None = None
    team_id: str | None = None
    session_id: str | None = None

    @property
    def visible_scopes(self) -> list[MemoryScope]:
        """
        Return scopes in priority order: L1 > L2 > L3 > L4.
        More specific layers override more abstract ones.
        """
        scopes = []
        if self.session_id:
            scopes.append(MemoryScope(layer=MemoryLayer.TMP, scope_id=self.session_id))
        if self.team_id:
            scopes.append(MemoryScope(layer=MemoryLayer.TEAM, scope_id=self.team_id))
        if self.project_id:
            scopes.append(MemoryScope(layer=MemoryLayer.PROJECT, scope_id=self.project_id))
        scopes.append(MemoryScope(layer=MemoryLayer.USER_SOUL, scope_id=self.user_id))
        return scopes


class CompactionHint(BaseModel):
    id: str
    scope_layer: str
    scope_id: str
    policy: str
    trigger_count: int = 0
    fired_at: datetime | None = None
    created_at: datetime


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
    memory_ctx: MemoryContext | None = None


class PendingResponse(BaseModel):
    items: list[ActionProposal]
    total: int


class StatusResponse(BaseModel):
    summary: str  # LLM-generated prose summary
    goal: str


class StrategyResponse(BaseModel):
    entries: list[StrategyEntry]


# ---- Conversation models ----

class Conversation(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class Message(BaseModel):
    id: str
    conversation_id: str
    role: str  # 'user' | 'assistant'
    content: str
    created_at: str


class ConversationListResponse(BaseModel):
    items: list[Conversation]
    total: int


class MessageListResponse(BaseModel):
    items: list[Message]
    total: int


class SendMessageRequest(BaseModel):
    content: str
    reasoning: bool = False  # Whether to enable LLM reasoning/thinking mode


class SendMessageResponse(BaseModel):
    user_message: Message
    assistant_message: Message
