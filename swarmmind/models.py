"""Pydantic models for SwarmMind."""

from enum import Enum

from pydantic import BaseModel, Field

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
    messages: list["Message"] | None = None


class Message(BaseModel):
    """Message within a conversation."""

    id: str
    conversation_id: str
    role: str  # 'user' | 'assistant' | 'tool'
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
    native_message: dict[str, object] | None = None


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


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    timestamp: str


class ReadyResponse(BaseModel):
    """Readiness check response."""

    status: str = "ok"
    runtime_profile_id: str
    runtime_instance_id: str


class DeleteProjectResponse(BaseModel):
    """Response after deleting a project."""

    status: str = "deleted"
    project_id: str


# ---- Project models ----


class ProjectMemberRole(str, Enum):
    """Minimal project member roles."""

    OWNER = "owner"
    EDITOR = "editor"
    APPROVER = "approver"
    VIEWER = "viewer"


class ProjectMemberStatus(str, Enum):
    """Project membership status."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class ProjectCapability(str, Enum):
    """Capabilities evaluated by minimal project RBAC."""

    VIEW_PROJECT = "view_project"
    RUN_PROJECT = "run_project"
    MANAGE_PROJECT = "manage_project"
    APPROVE_HIGH_RISK = "approve_high_risk"
    MANAGE_MEMBERS = "manage_members"


class ProjectMembership(BaseModel):
    """A human or service principal attached to one project."""

    membership_id: str
    project_id: str
    member_id: str
    display_name: str | None = None
    role: ProjectMemberRole = ProjectMemberRole.VIEWER
    status: ProjectMemberStatus = ProjectMemberStatus.ACTIVE
    capabilities: list[ProjectCapability] = []
    created_at: str
    updated_at: str


class ProjectMembershipListResponse(BaseModel):
    """Response containing project memberships."""

    items: list[ProjectMembership]
    total: int


class ProjectMembershipCreateRequest(BaseModel):
    """Request to add a project member."""

    member_id: str = Field(..., min_length=1, max_length=200)
    display_name: str | None = Field(None, max_length=200)
    role: ProjectMemberRole = ProjectMemberRole.VIEWER
    status: ProjectMemberStatus = ProjectMemberStatus.ACTIVE


class ProjectMembershipUpdateRequest(BaseModel):
    """Request to update a project member."""

    display_name: str | None = Field(None, max_length=200)
    role: ProjectMemberRole | None = None
    status: ProjectMemberStatus | None = None


class ProjectMembershipDeleteResponse(BaseModel):
    """Response after removing a project member."""

    status: str = "deleted"
    membership_id: str
    member_id: str


class ProjectPermissionCheckResponse(BaseModel):
    """Response for a minimal RBAC capability check."""

    project_id: str
    member_id: str
    capability: ProjectCapability
    allowed: bool
    role: ProjectMemberRole | None = None
    reason: str


class UserRole(str, Enum):
    """Local user role."""

    ADMIN = "admin"
    MEMBER = "member"


class UserStatus(str, Enum):
    """Local user status."""

    ACTIVE = "active"
    DISABLED = "disabled"


class User(BaseModel):
    """Local user identity."""

    user_id: str
    email: str
    display_name: str | None = None
    role: UserRole = UserRole.MEMBER
    status: UserStatus = UserStatus.ACTIVE
    created_at: str
    updated_at: str
    last_login_at: str | None = None


class UserListResponse(BaseModel):
    """Response containing users."""

    items: list[User]
    total: int


class UserCreateRequest(BaseModel):
    """Request to create a local user."""

    email: str = Field(..., min_length=3, max_length=320)
    display_name: str | None = Field(None, max_length=200)
    password: str = Field(..., min_length=8, max_length=200)
    role: UserRole = UserRole.MEMBER
    status: UserStatus = UserStatus.ACTIVE


class UserUpdateRequest(BaseModel):
    """Request to update a local user."""

    email: str | None = Field(None, min_length=3, max_length=320)
    display_name: str | None = Field(None, max_length=200)
    password: str | None = Field(None, min_length=8, max_length=200)
    role: UserRole | None = None
    status: UserStatus | None = None


class DeleteUserResponse(BaseModel):
    """Response after disabling a local user."""

    status: str = "disabled"
    user_id: str


class LoginRequest(BaseModel):
    """Request to exchange credentials for an API token."""

    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=1, max_length=200)
    token_name: str | None = Field(None, max_length=200)


class AuthToken(BaseModel):
    """API token returned once after login or token creation."""

    token_id: str
    token: str
    token_type: str = "bearer"  # noqa: S105 - token type label, not a secret.
    user: User


class CurrentUserResponse(BaseModel):
    """Current authenticated user and token context."""

    user: User
    token_id: str | None = None
    authenticated: bool = True


class LogoutResponse(BaseModel):
    """Response after revoking the current token."""

    status: str = "revoked"
    token_id: str


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
    conversation_id: str | None = None
    next_step: str | None = None
    phase: str | None = None
    risk_level: str | None = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    created_at: str
    updated_at: str


class ProjectCreateRequest(BaseModel):
    """Request to create a project manually."""

    title: str = Field(..., max_length=200)
    goal: str | None = Field(None, max_length=2000)
    scope: str | None = Field(None, max_length=2000)
    constraints: str | None = Field(None, max_length=2000)
    next_step: str | None = Field(None, max_length=1000)
    phase: str | None = Field(None, max_length=100)
    risk_level: str | None = Field(None, max_length=20)


class ProjectListResponse(BaseModel):
    """Response containing list of projects."""

    items: list[Project]
    total: int


class ProjectUpdateRequest(BaseModel):
    """Request to update a project."""

    title: str | None = Field(None, max_length=200)
    goal: str | None = Field(None, max_length=2000)
    scope: str | None = Field(None, max_length=2000)
    constraints: str | None = Field(None, max_length=2000)
    next_step: str | None = Field(None, max_length=1000)
    phase: str | None = Field(None, max_length=100)
    risk_level: str | None = Field(None, max_length=20)
    status: ProjectStatus | None = None


# ---- Artifact models ----


class Artifact(BaseModel):
    """Artifact/evidence metadata for a conversation."""

    artifact_id: str
    conversation_id: str | None = None
    message_id: str | None = None
    name: str | None = None
    path: str | None = None
    storage_uri: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    artifact_type: str | None = None
    created_at: str


class ArtifactListResponse(BaseModel):
    """Response containing list of artifacts."""

    items: list[Artifact]
    total: int


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


# ---- Auth setup / status models ----


class AuthStatusResponse(BaseModel):
    """Reports whether the instance has any registered users."""

    has_users: bool


class AuthSetupRequest(BaseModel):
    """Create the first admin user (only valid when no users exist)."""

    email: str
    password: str = Field(..., min_length=8)
    display_name: str | None = None
