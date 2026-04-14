"""Pydantic models for SwarmMind Phase 1."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Agent runtime status."""

    ACTIVE = "active"
    IDLE = "idle"
    ERROR = "error"


class ProposalStatus(str, Enum):
    """Status of an action proposal."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


class SupervisorDecision(str, Enum):
    """Human supervisor's decision on a proposal."""

    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class Agent(BaseModel):
    """Agent definition stored in the system."""

    agent_id: str
    domain: str
    system_prompt: str
    created_at: datetime


class WorkingMemoryEntry(BaseModel):
    """Single entry in the working memory store."""

    key: str
    value: str
    domain_tags: str | None = None
    last_writer_agent_id: str | None = None
    updated_at: datetime


class StrategyEntry(BaseModel):
    """Routing strategy for a specific situation."""

    situation_tag: str
    agent_id: str
    success_count: int = 0
    failure_count: int = 0


class ActionProposal(BaseModel):
    """Action proposal awaiting human approval."""

    id: str
    agent_id: str
    description: str
    target_resource: str | None = None
    preconditions: dict | None = None
    postconditions: dict | None = None
    confidence: float = 0.5
    status: ProposalStatus = ProposalStatus.PENDING
    created_at: datetime


class StrategyChangeProposal(BaseModel):
    """Proposal to change routing strategy for a situation."""

    id: str
    situation_tag: str
    proposed_agent_id: str
    reason: str | None = None
    status: ProposalStatus = ProposalStatus.PENDING
    proposed_at: datetime


class EventLogEntry(BaseModel):
    """Audit log entry for dispatched goals."""

    id: int | None = None
    timestamp: datetime
    goal: str
    situation_tag: str | None = None
    dispatched_agent_id: str | None = None
    action_proposal_id: str | None = None
    supervisor_decision: SupervisorDecision | None = None
    outcome: str | None = None
    latency_ms: int | None = None


# ---- Layered Memory models ----


class MemoryLayer(str, Enum):
    """Memory storage layers, from most persistent to most temporary."""

    USER_SOUL = "L4_user_soul"
    PROJECT = "L3_project"
    TEAM = "L2_team"
    TMP = "L1_tmp"


class MemoryScope(BaseModel):
    """Identifies a specific memory scope (layer + ID)."""

    layer: MemoryLayer
    scope_id: str


class MemoryEntry(BaseModel):
    """Single memory entry in the layered memory store."""

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
        """Return scopes in priority order: L1 > L2 > L3 > L4.
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
    """Hint for when to compact/merge memory entries."""

    id: str
    scope_layer: str
    scope_id: str
    policy: str
    trigger_count: int = 0
    fired_at: datetime | None = None
    created_at: datetime


# ---- API Request/Response models ----


class GoalRequest(BaseModel):
    """Request to dispatch a goal."""

    goal: str = Field(..., max_length=2000)


class ApproveRequest(BaseModel):
    """Request to approve a proposal."""

    id: str


class RejectRequest(BaseModel):
    """Request to reject a proposal."""

    id: str
    reason: str | None = None


class DispatchResponse(BaseModel):
    """Response from dispatching a goal."""

    action_proposal_id: str
    agent_id: str
    status: str
    memory_ctx: MemoryContext | None = None


class PendingResponse(BaseModel):
    """Response containing pending proposals."""

    items: list[ActionProposal]
    total: int


class StatusResponse(BaseModel):
    """Status response with LLM-generated summary."""

    summary: str  # LLM-generated prose summary
    goal: str


class StrategyResponse(BaseModel):
    """Response containing strategy table entries."""

    entries: list[StrategyEntry]


# ---- Conversation models ----


class Conversation(BaseModel):
    """Conversation record."""

    id: str
    title: str
    title_status: str = "pending"
    title_source: str | None = None
    title_generated_at: str | None = None
    runtime_profile_id: str | None = None
    runtime_instance_id: str | None = None
    thread_id: str | None = None
    created_at: str
    updated_at: str


class Message(BaseModel):
    """Message within a conversation."""

    id: str
    conversation_id: str
    role: str  # 'user' | 'assistant'
    content: str
    tool_call_id: str | None = None
    name: str | None = None
    created_at: str


class ConversationListResponse(BaseModel):
    """Response containing list of conversations."""

    items: list[Conversation]
    total: int


class MessageListResponse(BaseModel):
    """Response containing list of messages."""

    items: list[Message]
    total: int


class ConversationMode(str, Enum):
    """Conversation runtime mode."""

    FLASH = "flash"
    THINKING = "thinking"
    PRO = "pro"
    ULTRA = "ultra"


class ConversationRuntimeOptions(BaseModel):
    """Runtime options for a conversation."""

    mode: ConversationMode
    model_name: str | None = None
    thinking_enabled: bool
    plan_mode: bool
    subagent_enabled: bool


class RuntimeModelOption(BaseModel):
    """Available runtime model option."""

    name: str
    provider: str
    model: str
    display_name: str | None = None
    description: str | None = None
    supports_vision: bool = False
    is_default: bool = False


class RuntimeModelCatalogResponse(BaseModel):
    """Response containing available runtime models."""

    models: list[RuntimeModelOption]
    default_model: str | None = None
    subject_type: str
    subject_id: str


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""

    content: str
    mode: ConversationMode | None = None
    model_name: str | None = None
    reasoning: bool = False  # Whether to enable LLM reasoning/thinking mode


class SendMessageResponse(BaseModel):
    """Response containing user and assistant messages."""

    user_message: Message
    assistant_message: Message
