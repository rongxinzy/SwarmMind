"""Conversation-scoped trace orchestration helpers."""

from __future__ import annotations

import logging
from typing import Any

from swarmmind.services.trace_service import TraceService, trace_service

logger = logging.getLogger(__name__)


class ConversationTraceService:
    """Resolve conversation identity and delegate trace reconstruction."""

    def __init__(self, conversation_repo: Any, trace_reader: TraceService = trace_service) -> None:
        self._conversation_repo = conversation_repo
        self._trace_reader = trace_reader

    def get_trace(self, conversation_id: str) -> dict[str, Any]:
        """Load trace for a SwarmMind conversation, degrading gracefully on trace read errors."""
        conversation = self._conversation_repo.get_by_id(conversation_id)
        thread_id = self._resolve_thread_id(conversation, conversation_id)

        try:
            return self._trace_reader.get_conversation_trace(thread_id)
        except Exception as exc:
            logger.error("Failed to get trace for thread %s: %s", thread_id, exc)
            return self._trace_reader.build_error_trace(thread_id, f"读取轨迹失败: {exc!s}")

    @staticmethod
    def _resolve_thread_id(conversation: Any, conversation_id: str) -> str:
        """Prefer the bound runtime thread id, falling back to the conversation id."""
        return getattr(conversation, "thread_id", None) or conversation_id
