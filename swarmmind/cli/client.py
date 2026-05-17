"""HTTP-first SwarmMind supervisor API client used by the CLI."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from swarmmind.models import (
    ApprovalRequest,
    ApprovalRequestListResponse,
    AuditLogEntry,
    AuditLogListResponse,
    AuthToken,
    ConnectorCreateRequest,
    ConnectorHeartbeatRequest,
    ConnectorListResponse,
    ConnectorResponse,
    ConnectorUpdateRequest,
    Conversation,
    ConversationListResponse,
    ConversationTraceResponse,
    CreateApprovalRequest,
    CreateAuditLogEntry,
    CreateConversationRequest,
    CreateRunRequest,
    CreateTaskRequest,
    CurrentUserResponse,
    DeleteApprovalResponse,
    DeleteAuditLogResponse,
    DeleteConnectorResponse,
    DeleteConversationResponse,
    DeleteProjectResponse,
    DeleteTaskResponse,
    DeleteUserResponse,
    DispatchResponse,
    GoalRequest,
    HealthResponse,
    LoginRequest,
    LogoutResponse,
    MemoryEntry,
    MemoryListResponse,
    Project,
    ProjectCapability,
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectMembership,
    ProjectMembershipCreateRequest,
    ProjectMembershipDeleteResponse,
    ProjectMembershipListResponse,
    ProjectMembershipUpdateRequest,
    ProjectOverviewResponse,
    ProjectPermissionCheckResponse,
    ProjectUpdateRequest,
    ReadyResponse,
    Run,
    RunListResponse,
    SendMessageRequest,
    SendMessageResponse,
    Task,
    TaskListResponse,
    UpdateApprovalRequest,
    UpdateRunRequest,
    UpdateTaskRequest,
    User,
    UserCreateRequest,
    UserListResponse,
    UserUpdateRequest,
)

T = TypeVar("T", bound=BaseModel)

EXIT_ERROR = 1
EXIT_USAGE = 2
EXIT_BACKEND_UNAVAILABLE = 3
EXIT_NOT_FOUND = 4


class SwarmMindCLIError(Exception):
    """Normalized CLI-facing error with a stable exit code."""

    def __init__(self, message: str, *, exit_code: int = EXIT_ERROR, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code
        self.status_code = status_code


class BackendUnavailable(SwarmMindCLIError):
    """Raised when the supervisor API cannot be reached."""

    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=EXIT_BACKEND_UNAVAILABLE)


class ResourceNotFound(SwarmMindCLIError):
    """Raised for HTTP 404 responses."""

    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=EXIT_NOT_FOUND, status_code=404)


class ParameterError(SwarmMindCLIError):
    """Raised when command input cannot be converted to the shared API contract."""

    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=EXIT_USAGE)


class SwarmMindClient:
    """Thin HTTP client for the supervisor REST API."""

    def __init__(self, api_url: str, timeout: float = 30.0, api_token: str | None = None) -> None:
        self.api_url = api_url.rstrip("/")
        headers = {"Accept": "application/json"}
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"
        self._client = httpx.Client(
            base_url=self.api_url,
            timeout=httpx.Timeout(timeout, connect=5.0),
            headers=headers,
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> SwarmMindClient:
        return self

    def __exit__(self, *_exc_info) -> None:
        self.close()

    # ---- low-level request helpers ----

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        try:
            response = self._client.request(method, path, json=json_body, params=_compact(params))
        except httpx.ConnectError as exc:
            raise BackendUnavailable(f"Backend unavailable at {self.api_url}: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise BackendUnavailable(f"Backend timed out at {self.api_url}: {exc}") from exc
        except httpx.TransportError as exc:
            raise BackendUnavailable(f"Backend transport error at {self.api_url}: {exc}") from exc

        if response.status_code == 404:
            raise ResourceNotFound(_response_error_message(response, fallback="Resource not found"))
        if response.is_error:
            raise SwarmMindCLIError(
                _response_error_message(response, fallback=f"HTTP {response.status_code}"),
                status_code=response.status_code,
            )
        if response.status_code == 204:
            return None
        return _response_data(response)

    def _parse(self, model: type[T], data: Any) -> T:
        return model.model_validate(data)

    def _list(self, model: type[T], method: str, path: str, **kwargs) -> T:
        return self._parse(model, self._request(method, path, **kwargs))

    # ---- system ----

    def health(self) -> HealthResponse:
        return self._list(HealthResponse, "GET", "/health")

    def ready(self) -> ReadyResponse:
        return self._list(ReadyResponse, "GET", "/ready")

    # ---- auth / users ----

    def login(self, email: str, password: str, token_name: str | None = None) -> AuthToken:
        body = LoginRequest(email=email, password=password, token_name=token_name).model_dump(
            mode="json", exclude_none=True
        )
        return self._list(AuthToken, "POST", "/auth/login", json_body=body)

    def me(self) -> CurrentUserResponse:
        return self._list(CurrentUserResponse, "GET", "/auth/me")

    def logout(self) -> LogoutResponse:
        return self._list(LogoutResponse, "POST", "/auth/logout")

    def list_users(self) -> UserListResponse:
        return self._list(UserListResponse, "GET", "/users")

    def create_user(self, **fields) -> User:
        body = UserCreateRequest(**_compact(fields)).model_dump(mode="json", exclude_none=True)
        return self._list(User, "POST", "/users", json_body=body)

    def get_user(self, user_id: str) -> User:
        return self._list(User, "GET", f"/users/{user_id}")

    def update_user(self, user_id: str, **fields) -> User:
        body = UserUpdateRequest(**_compact(fields)).model_dump(mode="json", exclude_none=True)
        return self._list(User, "PATCH", f"/users/{user_id}", json_body=body)

    def delete_user(self, user_id: str) -> DeleteUserResponse:
        return self._list(DeleteUserResponse, "DELETE", f"/users/{user_id}")

    # ---- dispatch ----

    def dispatch(self, goal: str) -> DispatchResponse:
        body = GoalRequest(goal=goal).model_dump(mode="json")
        return self._list(DispatchResponse, "POST", "/dispatch", json_body=body)

    # ---- conversations / chat ----

    def list_conversations(self) -> ConversationListResponse:
        return self._list(ConversationListResponse, "GET", "/conversations")

    def create_conversation(self, title: str | None = None) -> Conversation:
        body = CreateConversationRequest(title=title).model_dump(mode="json", exclude_none=True)
        return self._list(Conversation, "POST", "/conversations", json_body=body)

    def recent_conversation(self) -> dict[str, Any] | None:
        return self._request("GET", "/conversations/recent")

    def search_conversations(self, query: str, limit: int = 20) -> ConversationListResponse:
        return self._list(ConversationListResponse, "GET", "/conversations/search", params={"q": query, "limit": limit})

    def get_conversation(self, conversation_id: str, *, include_messages: bool = False) -> Conversation:
        return self._list(
            Conversation,
            "GET",
            f"/conversations/{conversation_id}",
            params={"include_messages": include_messages},
        )

    def list_messages(self, conversation_id: str) -> dict[str, Any]:
        return self._request("GET", f"/conversations/{conversation_id}/messages")

    def send_message(
        self,
        conversation_id: str,
        content: str,
        *,
        mode: str | None = None,
        model_name: str | None = None,
        reasoning: bool = False,
    ) -> SendMessageResponse:
        body = _message_body(content, mode=mode, model_name=model_name, reasoning=reasoning)
        return self._list(SendMessageResponse, "POST", f"/conversations/{conversation_id}/messages", json_body=body)

    def stream_message(
        self,
        conversation_id: str,
        content: str,
        *,
        mode: str | None = None,
        model_name: str | None = None,
        reasoning: bool = False,
    ) -> Iterator[dict[str, Any]]:
        body = _message_body(content, mode=mode, model_name=model_name, reasoning=reasoning)
        yield from self._stream("POST", f"/conversations/{conversation_id}/messages/stream", json_body=body)

    def respond_to_clarification(self, conversation_id: str, tool_call_id: str, response: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/conversations/{conversation_id}/clarification",
            json_body={"tool_call_id": tool_call_id, "response": response},
        )

    def delete_conversation(self, conversation_id: str) -> DeleteConversationResponse:
        return self._list(DeleteConversationResponse, "DELETE", f"/conversations/{conversation_id}")

    def get_conversation_trace(self, conversation_id: str) -> ConversationTraceResponse:
        return self._list(ConversationTraceResponse, "GET", f"/conversations/{conversation_id}/trace")

    def export_conversation(self, conversation_id: str, export_format: str = "markdown") -> str:
        data = self._request("GET", f"/conversations/{conversation_id}/export", params={"format": export_format})
        if isinstance(data, (dict, list)):
            return json.dumps(data, ensure_ascii=False, indent=2)
        return str(data)

    # ---- projects ----

    def list_projects(self, *, limit: int | None = None, offset: int = 0) -> ProjectListResponse:
        return self._list(ProjectListResponse, "GET", "/projects", params={"limit": limit, "offset": offset})

    def create_project(self, **fields) -> Project:
        body = ProjectCreateRequest(**_compact(fields)).model_dump(mode="json", exclude_none=True)
        return self._list(Project, "POST", "/projects", json_body=body)

    def get_project(self, project_id: str) -> Project:
        return self._list(Project, "GET", f"/projects/{project_id}")

    def update_project(self, project_id: str, **fields) -> Project:
        body = ProjectUpdateRequest(**_compact(fields)).model_dump(mode="json", exclude_none=True)
        return self._list(Project, "PATCH", f"/projects/{project_id}", json_body=body)

    def delete_project(self, project_id: str) -> DeleteProjectResponse:
        return self._list(DeleteProjectResponse, "DELETE", f"/projects/{project_id}")

    def project_overview(self, project_id: str) -> ProjectOverviewResponse:
        return self._list(ProjectOverviewResponse, "GET", f"/projects/{project_id}/overview")

    def stream_project_message(
        self,
        project_id: str,
        content: str,
        *,
        mode: str | None = None,
        model_name: str | None = None,
        reasoning: bool = False,
    ) -> Iterator[dict[str, Any]]:
        body = _message_body(content, mode=mode, model_name=model_name, reasoning=reasoning)
        yield from self._stream("POST", f"/projects/{project_id}/messages/stream", json_body=body)

    # ---- project members ----

    def list_project_members(self, project_id: str) -> ProjectMembershipListResponse:
        return self._list(ProjectMembershipListResponse, "GET", f"/projects/{project_id}/members")

    def create_project_member(self, project_id: str, **fields) -> ProjectMembership:
        body = ProjectMembershipCreateRequest(**_compact(fields)).model_dump(mode="json", exclude_none=True)
        return self._list(ProjectMembership, "POST", f"/projects/{project_id}/members", json_body=body)

    def get_project_member(self, project_id: str, member_id: str) -> ProjectMembership:
        return self._list(ProjectMembership, "GET", f"/projects/{project_id}/members/{member_id}")

    def update_project_member(self, project_id: str, member_id: str, **fields) -> ProjectMembership:
        body = ProjectMembershipUpdateRequest(**_compact(fields)).model_dump(mode="json", exclude_none=True)
        return self._list(ProjectMembership, "PATCH", f"/projects/{project_id}/members/{member_id}", json_body=body)

    def delete_project_member(self, project_id: str, member_id: str) -> ProjectMembershipDeleteResponse:
        return self._list(ProjectMembershipDeleteResponse, "DELETE", f"/projects/{project_id}/members/{member_id}")

    def check_project_permission(
        self,
        project_id: str,
        member_id: str,
        capability: str,
    ) -> ProjectPermissionCheckResponse:
        checked = ProjectCapability(capability)
        return self._list(
            ProjectPermissionCheckResponse,
            "GET",
            f"/projects/{project_id}/members/{member_id}/permissions/{checked.value}",
        )

    # ---- runs ----

    def list_runs(self, *, project_id: str | None = None, conversation_id: str | None = None) -> RunListResponse:
        if project_id:
            return self._list(RunListResponse, "GET", f"/projects/{project_id}/runs")
        if conversation_id:
            return self._list(RunListResponse, "GET", f"/conversations/{conversation_id}/runs")
        raise SwarmMindCLIError("run list requires --project-id or --conversation-id")

    def get_run(self, run_id: str) -> Run:
        return self._list(Run, "GET", f"/runs/{run_id}")

    def create_run(self, **fields) -> Run:
        body = CreateRunRequest(**_compact(fields)).model_dump(mode="json", exclude_none=True)
        return self._list(Run, "POST", "/runs", json_body=body)

    def update_run(self, run_id: str, **fields) -> Run:
        body = UpdateRunRequest(**_compact(fields)).model_dump(mode="json", exclude_none=True)
        return self._list(Run, "PATCH", f"/runs/{run_id}", json_body=body)

    # ---- tasks ----

    def list_tasks(self, project_id: str) -> TaskListResponse:
        return self._list(TaskListResponse, "GET", f"/projects/{project_id}/tasks")

    def create_task(self, project_id: str, **fields) -> Task:
        body = CreateTaskRequest(**_compact(fields)).model_dump(mode="json", exclude_none=True)
        return self._list(Task, "POST", f"/projects/{project_id}/tasks", json_body=body)

    def get_task(self, project_id: str, task_id: str) -> Task:
        return self._list(Task, "GET", f"/projects/{project_id}/tasks/{task_id}")

    def update_task(self, project_id: str, task_id: str, **fields) -> Task:
        body = UpdateTaskRequest(**_compact(fields)).model_dump(mode="json", exclude_none=True)
        return self._list(Task, "PATCH", f"/projects/{project_id}/tasks/{task_id}", json_body=body)

    def delete_task(self, project_id: str, task_id: str) -> DeleteTaskResponse:
        return self._list(DeleteTaskResponse, "DELETE", f"/projects/{project_id}/tasks/{task_id}")

    # ---- approvals ----

    def list_approvals(
        self,
        *,
        project_id: str | None = None,
        status: str | None = None,
        risk_tier: str | None = None,
    ) -> ApprovalRequestListResponse:
        return self._list(
            ApprovalRequestListResponse,
            "GET",
            "/approvals",
            params={"project_id": project_id, "status": status, "risk_tier": risk_tier},
        )

    def create_approval(self, **fields) -> ApprovalRequest:
        body = CreateApprovalRequest(**_compact(fields)).model_dump(mode="json", exclude_none=True)
        return self._list(ApprovalRequest, "POST", "/approvals", json_body=body)

    def get_approval(self, approval_id: str) -> ApprovalRequest:
        return self._list(ApprovalRequest, "GET", f"/approvals/{approval_id}")

    def update_approval(self, approval_id: str, **fields) -> ApprovalRequest:
        body = UpdateApprovalRequest(**_compact(fields)).model_dump(mode="json", exclude_none=True)
        return self._list(ApprovalRequest, "PATCH", f"/approvals/{approval_id}", json_body=body)

    def delete_approval(self, approval_id: str) -> DeleteApprovalResponse:
        return self._list(DeleteApprovalResponse, "DELETE", f"/approvals/{approval_id}")

    # ---- audit logs ----

    def list_audit_logs(
        self,
        *,
        project_id: str | None = None,
        run_id: str | None = None,
        approval_id: str | None = None,
    ) -> AuditLogListResponse:
        return self._list(
            AuditLogListResponse,
            "GET",
            "/audit-logs",
            params={"project_id": project_id, "run_id": run_id, "approval_id": approval_id},
        )

    def create_audit_log(self, **fields) -> AuditLogEntry:
        body = CreateAuditLogEntry(**_compact(fields)).model_dump(mode="json", exclude_none=True)
        return self._list(AuditLogEntry, "POST", "/audit-logs", json_body=body)

    def get_audit_log(self, audit_id: str) -> AuditLogEntry:
        return self._list(AuditLogEntry, "GET", f"/audit-logs/{audit_id}")

    def delete_audit_log(self, audit_id: str) -> DeleteAuditLogResponse:
        return self._list(DeleteAuditLogResponse, "DELETE", f"/audit-logs/{audit_id}")

    # ---- memory ----

    def list_memory(
        self,
        *,
        layer: str | None = None,
        scope_id: str | None = None,
        tags: list[str] | None = None,
        limit: int = 100,
    ) -> MemoryListResponse:
        return self._list(
            MemoryListResponse,
            "GET",
            "/memory",
            params={"layer": layer, "scope_id": scope_id, "tag": tags, "limit": limit},
        )

    def get_memory(self, key: str, *, layer: str, scope_id: str) -> MemoryEntry:
        return self._list(MemoryEntry, "GET", f"/memory/{key}", params={"layer": layer, "scope_id": scope_id})

    # ---- stream ----

    # ---- connectors ----

    def list_connectors(self) -> ConnectorListResponse:
        """List all registered connectors."""
        return self._list(ConnectorListResponse, "GET", "/connectors")

    def create_connector(
        self,
        connector_type: str,
        name: str,
        config: dict[str, Any] | None = None,
        connector_id: str | None = None,
    ) -> ConnectorResponse:
        """Register a new connector."""
        body = ConnectorCreateRequest(
            connector_id=connector_id,
            name=name,
            connector_type=connector_type,
            config=config or {},
        ).model_dump(mode="json", exclude_none=True)
        return self._list(ConnectorResponse, "POST", "/connectors", json_body=body)

    def get_connector(self, connector_id: str) -> ConnectorResponse:
        """Get connector details."""
        return self._list(ConnectorResponse, "GET", f"/connectors/{connector_id}")

    def update_connector(
        self,
        connector_id: str,
        name: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> ConnectorResponse:
        """Update connector name or config."""
        body = ConnectorUpdateRequest(name=name, config=config).model_dump(mode="json", exclude_none=True)
        return self._list(ConnectorResponse, "PATCH", f"/connectors/{connector_id}", json_body=body)

    def delete_connector(self, connector_id: str) -> DeleteConnectorResponse:
        """Delete a connector."""
        return self._list(DeleteConnectorResponse, "DELETE", f"/connectors/{connector_id}")

    def connector_heartbeat(
        self,
        connector_id: str,
        status: str,
        mcp_url: str | None = None,
    ) -> ConnectorResponse:
        """Report connector health to the control plane."""
        body = ConnectorHeartbeatRequest(status=status, mcp_url=mcp_url).model_dump(mode="json", exclude_none=True)
        return self._list(ConnectorResponse, "POST", f"/connectors/{connector_id}/heartbeat", json_body=body)

    # ---- stream ----

    def _stream(self, method: str, path: str, *, json_body: dict[str, Any]) -> Iterator[dict[str, Any]]:
        timeout = httpx.Timeout(connect=5.0, read=None, write=30.0, pool=5.0)
        try:
            with self._client.stream(method, path, json=json_body, timeout=timeout) as response:
                if response.status_code == 404:
                    response.read()
                    raise ResourceNotFound(_response_error_message(response, fallback="Resource not found"))
                if response.is_error:
                    response.read()
                    raise SwarmMindCLIError(
                        _response_error_message(response, fallback=f"HTTP {response.status_code}"),
                        status_code=response.status_code,
                    )
                for line in response.iter_lines():
                    event = _parse_stream_line(line)
                    if event is not None:
                        yield event
        except httpx.ConnectError as exc:
            raise BackendUnavailable(f"Backend unavailable at {self.api_url}: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise BackendUnavailable(f"Backend stream timed out at {self.api_url}: {exc}") from exc
        except httpx.TransportError as exc:
            raise BackendUnavailable(f"Backend stream transport error at {self.api_url}: {exc}") from exc


def _compact(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if data is None:
        return None
    compacted = {k: v for k, v in data.items() if v is not None}
    return compacted


def _message_body(content: str, *, mode: str | None, model_name: str | None, reasoning: bool) -> dict[str, Any]:
    body = SendMessageRequest(content=content, mode=mode, model_name=model_name, reasoning=reasoning)
    return body.model_dump(mode="json", exclude_none=True)


def _response_data(response: httpx.Response) -> Any:
    content_type = response.headers.get("content-type", "")
    if "application/json" not in content_type:
        return response.text
    try:
        return response.json()
    except json.JSONDecodeError:
        return response.text


def _response_error_message(response: httpx.Response, *, fallback: str) -> str:
    try:
        payload = response.json()
    except json.JSONDecodeError:
        text = response.text.strip()
        return text or fallback

    detail = payload.get("detail") if isinstance(payload, dict) else None
    if isinstance(detail, str):
        return detail
    if detail is not None:
        return json.dumps(detail, ensure_ascii=False)
    return fallback


def _parse_stream_line(line: str) -> dict[str, Any] | None:
    stripped = line.strip()
    if not stripped:
        return None
    if stripped.startswith("data:"):
        stripped = stripped[5:].strip()
    if stripped == "[DONE]":
        return {"type": "done"}
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        return {"type": "raw", "text": stripped}
    return data if isinstance(data, dict) else {"type": "raw", "data": data}
