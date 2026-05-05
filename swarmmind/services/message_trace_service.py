"""Message-scoped trace summary service.

Translates raw TraceService checkpoint output into the product-facing
TraceSummaryResponse shape: step counts, subagent activity, artifacts,
blocked points, and a human-readable summary.
"""

from __future__ import annotations

import logging
from typing import Any

from swarmmind.models import TraceSummaryResponse
from swarmmind.services.conversation_trace_service import ConversationTraceService
from swarmmind.services.trace_service import trace_service

logger = logging.getLogger(__name__)


class MessageTraceService:
    """Produce a readable trace summary for a single assistant message.

    In the current implementation the summary covers the *conversation* trace
    anchored on the message's run.  As the runtime evolves this can be
    narrowed to a single-run slice.
    """

    def __init__(
        self,
        conversation_trace_service: ConversationTraceService,
        artifact_repo: Any | None = None,
    ) -> None:
        self._conversation_trace_service = conversation_trace_service
        self._artifact_repo = artifact_repo

    def get_summary(self, conversation_id: str, message_id: str) -> TraceSummaryResponse:
        """Return a TraceSummaryResponse for the given message.

        Degrades gracefully when the trace store is unreadable or empty.
        """
        try:
            trace = self._conversation_trace_service.get_trace(conversation_id)
        except Exception as exc:
            logger.warning("Trace read failed for conversation %s: %s", conversation_id, exc)
            return self._degraded_summary("执行轨迹暂不可读")

        events: list[dict[str, Any]] = trace.get("events", [])
        if not events:
            return self._degraded_summary("暂无执行记录")

        return self._build_summary_from_events(events)

    @staticmethod
    def _build_summary_from_events(events: list[dict[str, Any]]) -> TraceSummaryResponse:
        """Compute TraceSummaryResponse fields from a list of trace events."""
        steps_count = 0
        subagent_calls_count = 0
        artifacts_count = 0
        blocked_points: list[str] = []

        for event in events:
            event_type = event.get("type")

            if event_type == "subagent_dispatch":
                subagent_calls_count += 1
                steps_count += 1
            elif event_type == "tool_execution":
                steps_count += 1
                # Detect blocked points (clarification requests)
                tool_name = event.get("agent_id", "")
                if tool_name == "ask_clarification":
                    blocked_points.append(f"请求补充信息: {event.get('result', '')[:80]}")
            elif event_type == "assistant_response":
                steps_count += 1
            elif event_type == "artifact_created":
                artifacts_count += 1
                steps_count += 1
            elif event_type == "todos_updated":
                steps_count += 1
            elif event_type in ("task_started", "task_running", "task_completed", "task_failed"):
                steps_count += 1
                if event_type == "task_failed":
                    error = event.get("error") or event.get("content", "")
                    blocked_points.append(f"子任务失败: {str(error)[:80]}")

        summary = MessageTraceService._generate_human_summary(
            events=events,
            subagent_calls_count=subagent_calls_count,
            artifacts_count=artifacts_count,
            blocked_points=blocked_points,
        )

        return TraceSummaryResponse(
            steps_count=steps_count,
            subagent_calls_count=subagent_calls_count,
            artifacts_count=artifacts_count,
            blocked_points=blocked_points,
            summary=summary,
        )

    @staticmethod
    def _generate_human_summary(
        *,
        events: list[dict[str, Any]],
        subagent_calls_count: int,
        artifacts_count: int,
        blocked_points: list[str],
    ) -> str:
        """Generate a concise Chinese summary line."""
        if not events:
            return "暂无执行记录"

        parts: list[str] = []

        # Count user turns
        user_inputs = sum(1 for e in events if e.get("type") == "user_input")
        if user_inputs:
            parts.append(f"用户输入 {user_inputs} 轮")

        # Core execution stats
        exec_parts: list[str] = []
        if subagent_calls_count:
            exec_parts.append(f"子代理协作 {subagent_calls_count} 次")
        tool_calls = sum(1 for e in events if e.get("type") == "tool_execution")
        if tool_calls:
            exec_parts.append(f"工具调用 {tool_calls} 次")
        if artifacts_count:
            exec_parts.append(f"生成产物 {artifacts_count} 个")

        if exec_parts:
            parts.append("，".join(exec_parts))

        # Blocked state
        if blocked_points:
            parts.append(f"阻塞点 {len(blocked_points)} 个")

        if parts:
            return " → ".join(parts)

        return "执行完成"

    def extract_artifacts(
        self,
        conversation_id: str,
        project_id: str | None = None,
        run_id: str | None = None,
        task_id: str | None = None,
        author_role: str | None = None,
    ) -> list[dict[str, Any]]:
        """Extract artifact metadata from conversation trace and persist.

        Returns list of created artifact records. Idempotent: skips if artifact
        with same name already exists for the conversation.
        """
        if self._artifact_repo is None:
            logger.warning("Artifact repo not configured, skipping extraction")
            return []

        try:
            trace = self._conversation_trace_service.get_trace(conversation_id)
        except Exception as exc:
            logger.warning("Trace read failed for artifact extraction %s: %s", conversation_id, exc)
            return []

        events: list[dict[str, Any]] = trace.get("events", [])
        created: list[dict[str, Any]] = []
        existing_names = {a.name for a in self._artifact_repo.list_by_conversation(conversation_id) if a.name}

        for event in events:
            if event.get("type") != "artifact_created":
                continue
            name = event.get("artifact_path") or event.get("content", "")[:100]
            if name in existing_names:
                continue
            artifact = self._artifact_repo.create(
                conversation_id=conversation_id,
                project_id=project_id,
                message_id=None,
                name=name,
                path=name,
                artifact_type=event.get("artifact_type", "other"),
                run_id=event.get("run_id") or run_id,
                task_id=event.get("task_id") or task_id,
                author_role=event.get("author_role") or author_role,
            )
            created.append(
                {
                    "artifact_id": artifact.artifact_id,
                    "name": artifact.name,
                    "path": artifact.path,
                    "artifact_type": artifact.artifact_type,
                    "run_id": artifact.run_id,
                    "task_id": artifact.task_id,
                    "author_role": artifact.author_role,
                }
            )
            existing_names.add(name)

        return created

    @staticmethod
    def _degraded_summary(fallback_text: str) -> TraceSummaryResponse:
        return TraceSummaryResponse(
            steps_count=0,
            subagent_calls_count=0,
            artifacts_count=0,
            blocked_points=[],
            summary=fallback_text,
        )


def _default_message_trace_service() -> MessageTraceService:
    """Factory for the default service wired to global singletons."""
    from swarmmind.repositories.artifact import ArtifactRepository
    from swarmmind.repositories.conversation import ConversationRepository

    conv_repo = ConversationRepository()
    conv_trace_svc = ConversationTraceService(
        conversation_repo=conv_repo,
        trace_reader=trace_service,
    )
    return MessageTraceService(
        conversation_trace_service=conv_trace_svc,
        artifact_repo=ArtifactRepository(),
    )
