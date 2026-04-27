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
    promoted_project_id: str | None = None
    created_at: str
    updated_at: str
    messages: list["Message"] | None = None


class Message(BaseModel):
    """Message within a conversation."""

    id: str
    conversation_id: str
    role: str  # 'user' | 'assistant'
    content: str
    tool_call_id: str | None = None
    name: str | None = None
    run_id: str | None = None
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
    supports_thinking: bool = False
    capability_tags: list[str] = []
    is_default: bool = False


class RuntimeModelCatalogResponse(BaseModel):
    """Response containing available runtime models."""

    models: list[RuntimeModelOption]
    default_model: str | None = None
    subject_type: str
    subject_id: str


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""

    title: str | None = Field(None, max_length=200)


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


class RecentConversationResponse(BaseModel):
    """Response containing the most recent active conversation and its messages."""

    conversation: Conversation
    messages: list[Message]


class DeleteConversationResponse(BaseModel):
    """Response after deleting a conversation."""

    status: str = "deleted"
    id: str
    next_conversation_id: str | None = None


class ApproveResponse(BaseModel):
    """Response after approving a proposal."""

    status: str = "approved"
    id: str


class RejectResponse(BaseModel):
    """Response after rejecting a proposal."""

    status: str = "rejected"
    id: str
    reason: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    timestamp: str


class ReadyResponse(BaseModel):
    """Readiness check response."""

    status: str = "ok"
    runtime_profile_id: str
    runtime_instance_id: str


class ExtractArtifactsResponse(BaseModel):
    """Response after extracting artifacts from a conversation."""

    conversation_id: str
    extracted: int
    artifacts: list[dict]


class ConversationTraceResponse(BaseModel):
    """Response containing conversation execution trace."""

    conversation_id: str
    trace: dict | None = None


class DeleteProjectResponse(BaseModel):
    """Response after deleting a project."""

    status: str = "deleted"
    project_id: str


# ---- Project models ----


class ProjectStatus(str, Enum):
    """Project lifecycle status."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class Project(BaseModel):
    """Formal project execution boundary."""

    project_id: str
    title: str
    goal: str | None = None
    scope: str | None = None
    constraints: str | None = None
    source_conversation_id: str | None = None
    next_step: str | None = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    created_at: str
    updated_at: str


class ProjectCreateRequest(BaseModel):
    """Request to create a project manually."""

    title: str = Field(..., max_length=200)
    goal: str | None = Field(None, max_length=2000)
    scope: str | None = Field(None, max_length=2000)
    constraints: str | None = Field(None, max_length=2000)
    source_conversation_id: str | None = None
    next_step: str | None = Field(None, max_length=1000)


class ProjectListResponse(BaseModel):
    """Response containing list of projects."""

    items: list[Project]
    total: int


class PromoteConversationRequest(BaseModel):
    """Request to promote a conversation to a project."""

    title: str | None = Field(None, max_length=200)
    goal: str | None = Field(None, max_length=2000)
    scope: str | None = Field(None, max_length=2000)
    constraints: str | None = Field(None, max_length=2000)
    next_step: str | None = Field(None, max_length=1000)


class TraceSummaryResponse(BaseModel):
    """Readable execution trace summary attached to an assistant message."""

    steps_count: int = 0
    subagent_calls_count: int = 0
    artifacts_count: int = 0
    blocked_points: list[str] = []
    summary: str = ""


# ---- Artifact models ----


class Artifact(BaseModel):
    """Artifact/evidence metadata from a run."""

    artifact_id: str
    conversation_id: str
    message_id: str | None = None
    name: str | None = None
    artifact_type: str | None = None
    created_at: str


class ArtifactListResponse(BaseModel):
    """Response containing list of artifacts."""

    items: list[Artifact]
    total: int


class ProjectUpdateRequest(BaseModel):
    """Request to update a project."""

    title: str | None = Field(None, max_length=200)
    goal: str | None = Field(None, max_length=2000)
    scope: str | None = Field(None, max_length=2000)
    constraints: str | None = Field(None, max_length=2000)
    next_step: str | None = Field(None, max_length=1000)
    status: ProjectStatus | None = None


# ---- Run models ----


class RunStatus(str, Enum):
    """Run lifecycle status."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class Run(BaseModel):
    """Execution run anchored on project or conversation."""

    run_id: str
    project_id: str | None = None
    conversation_id: str
    status: RunStatus = RunStatus.RUNNING
    goal: str | None = None
    summary: str | None = None
    started_at: str
    completed_at: str | None = None


class RunListResponse(BaseModel):
    """Response containing list of runs."""

    items: list[Run]
    total: int


class CreateRunRequest(BaseModel):
    """Request to create a run."""

    conversation_id: str
    goal: str | None = Field(None, max_length=2000)
    status: RunStatus = RunStatus.RUNNING

# ---- LLM Provider models ----


class LlmProviderType(str, Enum):
    """Supported LLM provider types."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    GEMINI = "gemini"
    DASHSCOPE = "dashscope"
    MOONSHOT = "moonshot"
    MINIMAX = "minimax"
    DEEPSEEK = "deepseek"
    VLLM = "vllm"
    CUSTOM = "custom"


class LlmProviderModelEntry(BaseModel):
    """A model available through a provider."""

    model_name: str = Field(..., max_length=100)
    litellm_model: str = Field(..., max_length=200)
    display_name: str | None = Field(None, max_length=200)
    supports_vision: bool = False
    supports_thinking: bool = False
    fallback_model_names: list[str] = []
    is_enabled: bool = True


class LlmProvider(BaseModel):
    """LLM provider account."""

    provider_id: str
    name: str
    provider_type: LlmProviderType
    base_url: str | None = None
    is_enabled: bool = True
    is_default: bool = False
    created_at: str
    updated_at: str


class LlmProviderDetail(LlmProvider):
    """LLM provider with model list."""

    models: list[LlmProviderModelEntry] = []


class LlmProviderCreateRequest(BaseModel):
    """Request to create an LLM provider."""

    name: str = Field(..., max_length=200)
    provider_type: LlmProviderType
    api_key: str = Field(..., min_length=1)
    base_url: str | None = Field(None, max_length=500)
    is_default: bool = False
    models: list[LlmProviderModelEntry] = []


class LlmProviderUpdateRequest(BaseModel):
    """Request to update an LLM provider."""

    name: str | None = Field(None, max_length=200)
    api_key: str | None = Field(None, min_length=1)
    base_url: str | None = Field(None, max_length=500)
    is_enabled: bool | None = None
    is_default: bool | None = None
    models: list[LlmProviderModelEntry] | None = None


class LlmProviderListResponse(BaseModel):
    """Response containing list of providers."""

    items: list[LlmProvider]
    total: int


class GatewayKeyResponse(BaseModel):
    """Response containing the gateway API key."""

    gateway_key: str
    gateway_base_url: str


class GatewayStatusResponse(BaseModel):
    """Response containing gateway status and provider health."""

    gateway_ready: bool
    model_count: int
    providers: list[dict]
    config: dict
