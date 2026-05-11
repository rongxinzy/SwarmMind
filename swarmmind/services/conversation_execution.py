"""Conversation execution orchestration extracted from supervisor."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Generator
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException

from swarmmind.models import (
    ConversationRuntimeOptions,
    MemoryContext,
    Message,
    SendMessageRequest,
    SendMessageResponse,
)

if TYPE_CHECKING:
    from swarmmind.services.run_context import RunContext
    from swarmmind.services.run_lifecycle import RunLifecycleService


def _is_client_disconnect_error(exc: BaseException) -> bool:
    """Detect exceptions caused by the client closing the HTTP connection mid-stream."""
    if isinstance(exc, (ConnectionResetError, BrokenPipeError)):
        return True
    msg = str(exc).lower()
    indicators = (
        "bodystreambuffer",
        "stream buffer",
        "client disconnected",
        "connection reset",
        "broken pipe",
        "was aborted",
        "cancel",
    )
    return any(indicator in msg for indicator in indicators)


class ConversationExecutionService:
    """Execute sync/streaming conversation turns behind the API layer."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        conversation_repo: Any,
        message_repo: Any,
        action_proposal_repo: Any,
        runtime_adapter_cls: type,
        dispatch_fn: Callable[..., Any],
        derive_situation_tag_fn: Callable[[str], str],
        record_supervisor_decision_fn: Callable[[str, Any], None],
        approved_decision: Any,
        persist_user_message_fn: Callable[[str, str, str | None], Message],
        persist_assistant_message_fn: Callable[..., Message],
        maybe_generate_conversation_title_fn: Callable[[str], None],
        bind_conversation_runtime_fn: Callable[[str], tuple[object, str]],
        format_runtime_error_fn: Callable[[Exception], str],
        resolve_runtime_options_fn: Callable[[SendMessageRequest], ConversationRuntimeOptions],
        general_agent_status_labels_fn: Callable[[ConversationRuntimeOptions], tuple[str, str]],
        translate_general_agent_event_fn: Callable[[dict, ConversationRuntimeOptions], list[str]],
        serialize_stream_event_fn: Callable[..., str],
        db_to_message_fn: Callable[[Any], Message],
        execution_logger: logging.Logger,
        run_lifecycle_service: RunLifecycleService | None = None,
        approval_request_repo: Any | None = None,
    ) -> None:
        self._conversation_repo = conversation_repo
        self._message_repo = message_repo
        self._action_proposal_repo = action_proposal_repo
        self._runtime_adapter_cls = runtime_adapter_cls
        self._dispatch = dispatch_fn
        self._derive_situation_tag = derive_situation_tag_fn
        self._record_supervisor_decision = record_supervisor_decision_fn
        self._approved_decision = approved_decision
        self._persist_user_message = persist_user_message_fn
        self._persist_assistant_message = persist_assistant_message_fn
        self._maybe_generate_conversation_title = maybe_generate_conversation_title_fn
        self._bind_conversation_runtime = bind_conversation_runtime_fn
        self._format_runtime_error = format_runtime_error_fn
        self._resolve_runtime_options = resolve_runtime_options_fn
        self._general_agent_status_labels = general_agent_status_labels_fn
        self._translate_general_agent_event = translate_general_agent_event_fn
        self._serialize_stream_event = serialize_stream_event_fn
        self._db_to_message = db_to_message_fn
        self._logger = execution_logger
        self._run_lifecycle = run_lifecycle_service
        self._approval_request_repo = approval_request_repo

    def send_message(self, conversation_id: str, body: SendMessageRequest) -> SendMessageResponse:
        """Run a non-streaming conversation turn."""
        run_id = str(uuid.uuid4())
        user_msg = self._persist_user_message(conversation_id, body.content, run_id)
        memory_ctx = MemoryContext(user_id="supervisor", session_id=conversation_id)
        runtime_options = self._resolve_runtime_options(body)
        proposal_id = self._dispatch_and_approve(conversation_id, body.content)

        try:
            runtime_instance, _thread_id = self._bind_conversation_runtime(conversation_id)
            runtime_adapter = self._build_runtime_adapter(runtime_instance, runtime_options)
            completed_proposal = runtime_adapter.act(
                body.content,
                proposal_id,
                ctx=memory_ctx,
                runtime_options=runtime_options,
            )
            ai_response = completed_proposal.description
        except Exception as exc:  # pragma: no cover - exercised via supervisor tests
            self._logger.error("DeerFlowRuntimeAdapter execution error: %s", exc)
            ai_response = self._format_runtime_error(exc)

        assistant_msg = self._persist_assistant_message(conversation_id, ai_response)
        self._maybe_generate_conversation_title(conversation_id)
        return SendMessageResponse(user_message=user_msg, assistant_message=assistant_msg)

    def stream_message(
        self,
        conversation_id: str,
        body: SendMessageRequest,
        *,
        run_context: RunContext | None = None,
    ) -> Generator[str, None, None]:
        """Stream a conversation turn with runtime-status events.

        When run_context is provided and has a project_id, lifecycle events are
        persisted via RunLifecycleService. ChatSession-only calls pass no
        run_context and are unaffected.
        """
        run_id = run_context.run_id if run_context is not None else str(uuid.uuid4())

        if self._run_lifecycle is not None and run_context is not None:
            self._run_lifecycle.start(run_context)

        user_message = self._persist_user_message(conversation_id, body.content, run_id)
        yield self._serialize_stream_event("status", phase="accepted", label="消息已加入当前会话")
        yield self._serialize_stream_event(
            "user_message",
            message={
                "id": user_message.id,
                "role": user_message.role,
                "content": user_message.content,
                "created_at": user_message.created_at,
            },
        )

        memory_ctx = MemoryContext(user_id="supervisor", session_id=conversation_id)
        runtime_options = self._resolve_runtime_options(body)
        routing_label, running_label = self._general_agent_status_labels(runtime_options)

        # Capability guard tracking — populated by the middleware callback.
        guard_event: dict | None = None

        def _on_guard(capability: str, risk_tier: str, evidence: dict) -> None:
            nonlocal guard_event
            guard_event = {"capability": capability, "risk_tier": risk_tier, "evidence": evidence}

        ai_response = ""
        try:
            yield self._serialize_stream_event("status", phase="routing", label=routing_label)

            self._dispatch_and_approve(conversation_id, body.content)
            runtime_instance, _thread_id = self._bind_conversation_runtime(conversation_id)
            runtime_adapter = self._build_runtime_adapter(
                runtime_instance, runtime_options, run_context=run_context, on_guard=_on_guard
            )

            yield self._serialize_stream_event("status", phase="running", label=running_label)

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
                        self._logger.info("Stream event #%d: type=%s", event_count, event.get("type"))
                except StopIteration as stop:
                    ai_response, _tool_results = stop.value
                    self._logger.info("Stream completed: events=%d, response_length=%d", event_count, len(ai_response))
                    break
                except Exception as stream_error:
                    self._logger.error("Stream event error: %s", stream_error, exc_info=True)
                    raise

                try:
                    for line in self._translate_general_agent_event(event, runtime_options):
                        yield line
                except Exception as translate_error:
                    self._logger.error("Event translation error: %s, event=%s", translate_error, event)
                    raise

            if not ai_response.strip():
                ai_response = "本轮运行已完成，但没有生成可展示的最终回答。"
        except HTTPException:
            raise
        except Exception as exc:
            if _is_client_disconnect_error(exc):
                self._logger.info("Client disconnected from stream: %s", exc)
                return
            self._logger.error("Conversation stream error: %s", exc, exc_info=True)
            if self._run_lifecycle is not None and run_context is not None:
                error_class = "TIMEOUT" if isinstance(exc, TimeoutError) else "RUNTIME_ERROR"
                self._run_lifecycle.fail(run_context, error_class, str(exc))
            ai_response = self._format_runtime_error(exc)
            error_code = "TIMEOUT" if isinstance(exc, TimeoutError) else "RUNTIME_ERROR"
            yield self._serialize_stream_event("error", code=error_code, message=ai_response)

        # Capability guard: create ApprovalRequest and pause the run.
        if guard_event is not None and run_context is not None and run_context.project_id is not None:
            yield from self._handle_capability_guard(run_context, guard_event)
            return  # do NOT call finish() — run stays in waiting_approval

        if self._run_lifecycle is not None and run_context is not None:
            summary = ai_response[:500] if ai_response else None
            self._run_lifecycle.finish(run_context, summary)

        assistant_message = self._persist_assistant_message(conversation_id, ai_response, run_id=run_id)
        self._maybe_generate_conversation_title(conversation_id)
        conversation = self._conversation_repo.get_by_id(conversation_id)
        serialized_conversation = {
            "id": conversation.id,
            "title": conversation.title,
            "title_status": conversation.title_status,
            "title_source": conversation.title_source,
            "title_generated_at": (
                str(conversation.title_generated_at) if conversation.title_generated_at is not None else None
            ),
            "updated_at": str(conversation.updated_at) if conversation.updated_at is not None else "",
        }

        yield self._serialize_stream_event(
            "assistant_final",
            message={
                "id": assistant_message.id,
                "role": assistant_message.role,
                "content": assistant_message.content,
                "created_at": assistant_message.created_at,
            },
        )
        yield self._serialize_stream_event("title", conversation=serialized_conversation)
        yield self._serialize_stream_event("status", phase="completed", label="本轮会话已完成")
        yield self._serialize_stream_event("done")

    def _handle_capability_guard(self, run_context: RunContext, guard_event: dict) -> Generator[str, None, None]:
        """Create an ApprovalRequest, pause the run, and emit a waiting_approval event."""
        capability = guard_event.get("capability", "unknown")
        risk_tier = guard_event.get("risk_tier", "high")
        evidence = guard_event.get("evidence", {})

        approval_id: str | None = None
        if self._approval_request_repo is not None:
            try:
                approval = self._approval_request_repo.create(
                    project_id=run_context.project_id,
                    run_id=run_context.run_id,
                    title=f"需要审批：{capability}",
                    description=f"运行请求执行风险等级为 {risk_tier} 的能力：{capability}",
                    risk_tier=risk_tier,
                    requested_capability=capability,
                    evidence=str(evidence),
                    approver_role=run_context.approver_role,
                    recovery_behavior="re_execute",
                )
                approval_id = approval.approval_id
                self._logger.info(
                    "ApprovalRequest created: approval_id=%s run_id=%s capability=%s",
                    approval_id,
                    run_context.run_id,
                    capability,
                )
            except Exception:
                self._logger.exception("Failed to create ApprovalRequest for capability guard")

        if self._run_lifecycle is not None and approval_id is not None:
            self._run_lifecycle.pause_for_approval(run_context, approval_id)

        yield self._serialize_stream_event(
            "status.waiting_approval",
            approval_id=approval_id,
            capability=capability,
            risk_tier=risk_tier,
            run_id=run_context.run_id,
            project_id=run_context.project_id,
        )
        yield self._serialize_stream_event("status", phase="waiting_approval", label="等待审批中")
        yield self._serialize_stream_event("done")

    def respond_to_clarification(self, conversation_id: str, tool_call_id: str, response: str) -> Message:
        """Persist a clarification response through the normal message path."""
        self._conversation_repo.get_by_id(conversation_id)
        result = self._message_repo.create(
            conversation_id=conversation_id,
            role="tool",
            content=response,
            tool_call_id=tool_call_id,
            name="ask_clarification_response",
        )
        self._conversation_repo.touch(conversation_id)
        return self._db_to_message(result)

    def _dispatch_and_approve(self, conversation_id: str, content: str) -> str:
        situation_tag = self._derive_situation_tag(content)
        dispatch_result = self._dispatch(
            content,
            user_id="supervisor",
            session_id=conversation_id,
            override_situation_tag=situation_tag,
        )
        proposal_id = dispatch_result.action_proposal_id
        self._action_proposal_repo.approve(proposal_id)
        self._record_supervisor_decision(proposal_id, self._approved_decision)
        return proposal_id

    def _build_runtime_adapter(
        self,
        runtime_instance: object,
        runtime_options: ConversationRuntimeOptions,
        *,
        run_context: RunContext | None = None,
        on_guard=None,
    ):
        middlewares = None
        if run_context is not None and run_context.project_id is not None and on_guard is not None:
            from swarmmind.agents.middlewares.capability_guard_middleware import CapabilityGuardMiddleware
            from swarmmind.services.run_context import RiskPolicy

            if run_context.risk_policy != RiskPolicy.PERMISSIVE:
                middlewares = [CapabilityGuardMiddleware(risk_policy=run_context.risk_policy, on_guard=on_guard)]

        kwargs: dict = {
            "runtime_instance": runtime_instance,
            "default_model": runtime_options.model_name,
            "thinking_enabled": runtime_options.thinking_enabled,
            "subagent_enabled": runtime_options.subagent_enabled,
            "plan_mode": runtime_options.plan_mode,
        }
        if middlewares is not None:
            kwargs["middlewares"] = middlewares
        return self._runtime_adapter_cls(**kwargs)
