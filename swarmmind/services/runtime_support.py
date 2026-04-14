"""Runtime support helpers extracted from supervisor orchestration."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any

from fastapi import HTTPException

from swarmmind.models import ConversationMode, ConversationRuntimeOptions, SendMessageRequest
from swarmmind.repositories.conversation import ConversationRepository
from swarmmind.runtime import (
    RuntimeConfigError,
    RuntimeExecutionError,
    RuntimeUnavailableError,
    ensure_default_runtime_instance,
)
from swarmmind.runtime.catalog import (
    ANONYMOUS_SUBJECT_ID,
    ANONYMOUS_SUBJECT_TYPE,
    resolve_model_for_subject,
)

logger = logging.getLogger(__name__)

MODE_RUNTIME_MAP: dict[ConversationMode, dict[str, bool]] = {
    ConversationMode.FLASH: {
        "thinking_enabled": False,
        "plan_mode": False,
        "subagent_enabled": False,
    },
    ConversationMode.THINKING: {
        "thinking_enabled": True,
        "plan_mode": False,
        "subagent_enabled": False,
    },
    ConversationMode.PRO: {
        "thinking_enabled": True,
        "plan_mode": True,
        "subagent_enabled": False,
    },
    ConversationMode.ULTRA: {
        "thinking_enabled": True,
        "plan_mode": True,
        "subagent_enabled": True,
    },
}


def normalize_model_name(model_name: str | None) -> str | None:
    """Trim a user-supplied model name and collapse blank values to None."""
    if model_name is None:
        return None

    value = model_name.strip()
    return value or None


def conversation_thread_id(conversation_id: str) -> str:
    """Map a conversation to its DeerFlow thread identifier."""
    return conversation_id


def format_runtime_error(exc: Exception) -> str:
    """Normalize runtime exceptions into user-facing error strings."""
    if isinstance(exc, (RuntimeConfigError, RuntimeUnavailableError, RuntimeExecutionError)):
        return f"DeerFlow Runtime error: {exc}"
    return f"Unexpected DeerFlow execution error: {exc}"


class RuntimeSupportService:
    """Lightweight runtime support API for conversation execution orchestration."""

    def __init__(
        self,
        conversation_repo: ConversationRepository,
        mode_runtime_map: Mapping[ConversationMode, Mapping[str, bool]] = MODE_RUNTIME_MAP,
        resolve_model_for_subject_fn: Callable[..., Any] = resolve_model_for_subject,
        ensure_default_runtime_instance_fn: Callable[[], Any] = ensure_default_runtime_instance,
        subject_type: str = ANONYMOUS_SUBJECT_TYPE,
        subject_id: str = ANONYMOUS_SUBJECT_ID,
    ) -> None:
        self._conversation_repo = conversation_repo
        self._mode_runtime_map = mode_runtime_map
        self._resolve_model_for_subject_fn = resolve_model_for_subject_fn
        self._ensure_default_runtime_instance_fn = ensure_default_runtime_instance_fn
        self._subject_type = subject_type
        self._subject_id = subject_id

    def normalize_model_name(self, model_name: str | None) -> str | None:
        """Normalize a requested model name before catalog resolution."""
        return normalize_model_name(model_name)

    def resolve_model_name_for_request(self, model_name: str | None) -> str:
        """Resolve the effective runtime model or raise an HTTP-friendly error."""
        normalized_model_name = self.normalize_model_name(model_name)
        try:
            selected_model = self._resolve_model_for_subject_fn(
                requested_model_name=normalized_model_name,
                subject_type=self._subject_type,
                subject_id=self._subject_id,
            )
        except RuntimeConfigError as exc:
            raise HTTPException(
                status_code=400 if normalized_model_name else 503,
                detail=str(exc),
            ) from exc
        return selected_model.name

    def conversation_thread_id(self, conversation_id: str) -> str:
        """Return the runtime thread identifier for a conversation."""
        return conversation_thread_id(conversation_id)

    def bind_conversation_runtime(self, conversation_id: str) -> tuple[object, str]:
        """Bind the default runtime instance metadata onto the conversation."""
        runtime_instance = self._ensure_default_runtime_instance_fn()
        thread_id = self.conversation_thread_id(conversation_id)

        self._conversation_repo.update_runtime(
            conversation_id,
            runtime_instance.runtime_profile_id,
            runtime_instance.runtime_instance_id,
            thread_id,
        )

        return runtime_instance, thread_id

    def format_runtime_error(self, exc: Exception) -> str:
        """Convert runtime failures into a stable user-facing message."""
        return format_runtime_error(exc)

    def resolve_runtime_options(self, body: SendMessageRequest) -> ConversationRuntimeOptions:
        """Map request flags and mode selection into runtime execution options."""
        effective_mode = body.mode
        logger.info(
            "[DEBUG] _resolve_runtime_options: body.mode=%s, effective_mode=%s",
            body.mode,
            effective_mode,
        )
        if effective_mode is None:
            effective_mode = ConversationMode.THINKING if body.reasoning else ConversationMode.FLASH

        runtime_flags = self._mode_runtime_map[effective_mode]
        logger.info("[DEBUG] _resolve_runtime_options: runtime_flags=%s", runtime_flags)
        options = ConversationRuntimeOptions(
            mode=effective_mode,
            model_name=self.resolve_model_name_for_request(body.model_name),
            thinking_enabled=runtime_flags["thinking_enabled"],
            plan_mode=runtime_flags["plan_mode"],
            subagent_enabled=runtime_flags["subagent_enabled"],
        )
        logger.info(
            "[DEBUG] _resolve_runtime_options: returning options with subagent_enabled=%s",
            options.subagent_enabled,
        )
        return options
