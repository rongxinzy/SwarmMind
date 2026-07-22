"""Conversation execution orchestration extracted from supervisor."""

from __future__ import annotations

import inspect
import json
import logging
import uuid
from collections.abc import Callable, Generator
from typing import Any

from fastapi import HTTPException

from swarmmind.models import (
    ConversationRuntimeOptions,
    Message,
    SendMessageRequest,
    SendMessageResponse,
)
from swarmmind.services.artifact_content import is_virtual_user_data_path, normalize_virtual_path

logger = logging.getLogger(__name__)


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
        runtime_cls: type | None = None,
        persist_user_message_fn: Callable[[str, str], Message],
        persist_assistant_message_fn: Callable[..., Message],
        maybe_generate_conversation_title_fn: Callable[[str], None],
        bind_conversation_runtime_fn: Callable[[str], tuple[object, str]],
        format_runtime_error_fn: Callable[[Exception], str],
        resolve_runtime_options_fn: Callable[[SendMessageRequest], ConversationRuntimeOptions],
        deerflow_runtime_status_labels_fn: Callable[[ConversationRuntimeOptions], tuple[str, str]],
        translate_deerflow_runtime_event_fn: Callable[[dict, ConversationRuntimeOptions], list[str]],
        serialize_stream_event_fn: Callable[..., str],
        db_to_message_fn: Callable[[Any], Message],
        execution_logger: logging.Logger,
        artifact_repo: Any | None = None,
    ) -> None:
        self._conversation_repo = conversation_repo
        self._message_repo = message_repo
        if runtime_cls is None:
            raise ValueError("runtime_cls is required")
        self._runtime_cls = runtime_cls
        self._persist_user_message = persist_user_message_fn
        self._persist_assistant_message = persist_assistant_message_fn
        self._maybe_generate_conversation_title = maybe_generate_conversation_title_fn
        self._bind_conversation_runtime = bind_conversation_runtime_fn
        self._format_runtime_error = format_runtime_error_fn
        self._resolve_runtime_options = resolve_runtime_options_fn
        self._deerflow_runtime_status_labels = deerflow_runtime_status_labels_fn
        self._translate_deerflow_runtime_event = translate_deerflow_runtime_event_fn
        self._serialize_stream_event = serialize_stream_event_fn
        self._db_to_message = db_to_message_fn
        self._logger = execution_logger
        self._artifact_repo = artifact_repo

    def send_message(self, conversation_id: str, body: SendMessageRequest) -> SendMessageResponse:
        """Run a non-streaming conversation turn."""
        user_msg = self._persist_user_message(conversation_id, body.content)
        runtime_options = self._resolve_runtime_options(body)

        try:
            runtime_instance, _thread_id = self._bind_conversation_runtime(conversation_id)
            runtime = self._build_runtime(runtime_instance, runtime_options)
            ai_response = runtime.run_turn(
                body.content,
                conversation_id=conversation_id,
                runtime_options=runtime_options,
            )
        except Exception as exc:  # pragma: no cover - exercised via supervisor tests
            self._logger.error("DeerFlow runtime execution error: %s", exc)
            ai_response = self._format_runtime_error(exc)

        assistant_msg = self._persist_assistant_message(conversation_id, ai_response)
        self._maybe_generate_conversation_title(conversation_id)
        return SendMessageResponse(user_message=user_msg, assistant_message=assistant_msg)

    def stream_message(
        self,
        conversation_id: str,
        body: SendMessageRequest,
    ) -> Generator[str, None, None]:
        """Stream a conversation turn with runtime-status events."""
        run_id = str(uuid.uuid4())

        user_message, native_user_payload = self._persist_user_turn(conversation_id, body, run_id)
        yield self._serialize_stream_event("status", phase="accepted", label="消息已加入当前会话")
        yield self._serialize_stream_event(
            "deerflow.message",
            message=native_user_payload
            or {
                "id": user_message.id,
                "type": "human",
                "content": user_message.content,
                "additional_kwargs": {},
                "response_metadata": {},
            },
        )

        runtime_options = self._resolve_runtime_options(body)
        routing_label, running_label = self._deerflow_runtime_status_labels(runtime_options)

        native_assistant_message: Message | None = None

        ai_response = ""
        try:
            yield self._serialize_stream_event("status", phase="routing", label=routing_label)

            runtime_instance, _thread_id = self._bind_conversation_runtime(conversation_id)
            runtime = self._build_runtime(runtime_instance, runtime_options)

            yield self._serialize_stream_event("status", phase="running", label=running_label)

            stream_kwargs = {
                "conversation_id": conversation_id,
                "runtime_options": runtime_options,
            }
            if "native_messages" in inspect.signature(runtime.stream_events).parameters:
                stream_kwargs["native_messages"] = True
            stream = runtime.stream_events(body.content, **stream_kwargs)
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
                    if event.get("type") == "deerflow.message":
                        native_message = event.get("message")
                        if not event.get("transient") and isinstance(native_message, dict):
                            persisted = self._persist_native_deerflow_message(
                                conversation_id,
                                native_message,
                                run_id=run_id,
                            )
                            self._register_native_message_artifacts(
                                conversation_id,
                                native_message,
                                message_id=persisted.id,
                            )
                            if persisted.role == "assistant" and persisted.content.strip():
                                native_assistant_message = persisted
                        yield self._serialize_stream_event("deerflow.message", message=event.get("message"))
                    elif event.get("type") == "values":
                        self._register_artifact_paths(
                            conversation_id,
                            event.get("artifacts"),
                            artifact_type="present_files",
                        )
                    for line in self._translate_deerflow_runtime_event(event, runtime_options):
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
            ai_response = self._format_runtime_error(exc)
            error_code = "TIMEOUT" if isinstance(exc, TimeoutError) else "RUNTIME_ERROR"
            yield self._serialize_stream_event("error", code=error_code, message=ai_response)

        assistant_message = native_assistant_message
        if assistant_message is None:
            assistant_message = self._persist_assistant_message(conversation_id, ai_response)
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

    def stream_native_message(
        self,
        conversation_id: str,
        body: SendMessageRequest,
    ) -> Generator[str, None, None]:
        """Stream a turn for the Next.js DeerFlow-native chat path."""
        run_id = str(uuid.uuid4())

        user_message, native_user_payload = self._persist_user_turn(conversation_id, body, run_id)
        yield self._serialize_stream_event(
            "deerflow.message",
            message=native_user_payload
            or {
                "id": user_message.id,
                "type": "human",
                "content": user_message.content,
                "additional_kwargs": {},
                "response_metadata": {},
            },
        )

        runtime_options = self._resolve_runtime_options(body)
        native_assistant_message: Message | None = None
        ai_response = ""

        try:
            runtime_instance, _thread_id = self._bind_conversation_runtime(conversation_id)
            runtime = self._build_runtime(runtime_instance, runtime_options)

            stream_kwargs = {
                "conversation_id": conversation_id,
                "runtime_options": runtime_options,
            }
            if "native_messages" in inspect.signature(runtime.stream_events).parameters:
                stream_kwargs["native_messages"] = True
            stream = runtime.stream_events(body.content, **stream_kwargs)

            event_count = 0
            while True:
                try:
                    event = next(stream)
                    event_count += 1
                    if event_count <= 5 or event_count % 10 == 0:
                        self._logger.info("Native stream event #%d: type=%s", event_count, event.get("type"))
                except StopIteration as stop:
                    ai_response, _tool_results = stop.value
                    self._logger.info(
                        "Native stream completed: events=%d, response_length=%d", event_count, len(ai_response)
                    )
                    break
                except Exception as stream_error:
                    self._logger.error("Native stream event error: %s", stream_error, exc_info=True)
                    raise

                event_type = event.get("type")
                if event_type == "deerflow.message":
                    native_message = event.get("message")
                    if not event.get("transient") and isinstance(native_message, dict):
                        persisted = self._persist_native_deerflow_message(
                            conversation_id,
                            native_message,
                            run_id=run_id,
                        )
                        self._register_native_message_artifacts(
                            conversation_id,
                            native_message,
                            message_id=persisted.id,
                        )
                        if persisted.role == "assistant" and persisted.content.strip():
                            native_assistant_message = persisted
                    yield self._serialize_stream_event("deerflow.message", message=native_message)
                elif event_type == "plan_steps":
                    steps = event.get("steps")
                    if isinstance(steps, list):
                        yield self._serialize_stream_event("plan_steps", steps=steps)
                elif event_type == "values":
                    self._register_artifact_paths(
                        conversation_id,
                        event.get("artifacts"),
                        artifact_type="present_files",
                    )

            if not ai_response.strip():
                ai_response = "本轮运行已完成，但没有生成可展示的最终回答。"
        except HTTPException:
            raise
        except Exception as exc:
            if _is_client_disconnect_error(exc):
                self._logger.info("Client disconnected from native stream: %s", exc)
                return
            self._logger.error("Native conversation stream error: %s", exc, exc_info=True)
            ai_response = self._format_runtime_error(exc)
            error_code = "TIMEOUT" if isinstance(exc, TimeoutError) else "RUNTIME_ERROR"
            yield self._serialize_stream_event("error", code=error_code, message=ai_response)

        assistant_message = native_assistant_message
        if assistant_message is None:
            assistant_message = self._persist_assistant_message(conversation_id, ai_response)
            yield self._serialize_stream_event(
                "deerflow.message",
                message={
                    "id": assistant_message.id,
                    "type": "ai",
                    "content": assistant_message.content,
                    "additional_kwargs": {},
                    "response_metadata": {},
                },
            )

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

        yield self._serialize_stream_event("title", conversation=serialized_conversation)
        yield self._serialize_stream_event("done")

    def _persist_user_turn(
        self,
        conversation_id: str,
        body: SendMessageRequest,
        run_id: str,
    ) -> tuple[Message, dict[str, Any] | None]:
        """Persist the user's turn, preserving native LangGraph metadata when provided."""
        native_message = body.native_message if isinstance(body.native_message, dict) else None
        if not native_message or native_message.get("type") != "human":
            return self._persist_user_message(conversation_id, body.content), None

        message_id = str(uuid.uuid4())
        additional_kwargs = native_message.get("additional_kwargs")
        response_metadata = native_message.get("response_metadata")
        payload = {
            **native_message,
            "id": message_id,
            "type": "human",
            "content": body.content,
            "additional_kwargs": additional_kwargs if isinstance(additional_kwargs, dict) else {},
            "response_metadata": response_metadata if isinstance(response_metadata, dict) else {},
        }
        row = self._message_repo.create(
            conversation_id=conversation_id,
            role="user",
            content=body.content,
            native_payload=payload,
            message_id=message_id,
        )
        self._conversation_repo.touch(conversation_id)
        return self._db_to_message(row), payload

    def _persist_native_deerflow_message(
        self,
        conversation_id: str,
        native_message: dict[str, Any],
        *,
        run_id: str,
    ) -> Message:
        """Persist a complete LangGraph/DeerFlow message without flattening it."""
        message_type = native_message.get("type")
        role = {"human": "user", "ai": "assistant", "tool": "tool"}.get(
            str(message_type), str(message_type or "assistant")
        )
        row = self._message_repo.create(
            conversation_id=conversation_id,
            role=role,
            content=self._native_message_text(native_message.get("content")),
            tool_call_id=(
                str(native_message["tool_call_id"]) if native_message.get("tool_call_id") is not None else None
            ),
            name=(str(native_message["name"]) if native_message.get("name") is not None else None),
            native_payload=native_message,
        )
        self._conversation_repo.touch(conversation_id)
        return self._db_to_message(row)

    def _register_native_message_artifacts(
        self,
        conversation_id: str,
        native_message: dict[str, Any],
        *,
        message_id: str | None,
    ) -> None:
        if native_message.get("type") != "ai":
            return

        for tool_call in native_message.get("tool_calls") or []:
            if not isinstance(tool_call, dict):
                continue
            tool_name = str(tool_call.get("name") or "")
            args = tool_call.get("args") if isinstance(tool_call.get("args"), dict) else {}
            if tool_name == "present_files":
                self._register_artifact_paths(
                    conversation_id,
                    args.get("filepaths"),
                    artifact_type="present_files",
                    message_id=message_id,
                )
            elif tool_name in {"write_file", "str_replace"}:
                self._register_artifact_paths(
                    conversation_id,
                    [args.get("path")],
                    artifact_type=tool_name,
                    message_id=message_id,
                )

    def _register_artifact_paths(
        self,
        conversation_id: str,
        paths: Any,
        *,
        artifact_type: str,
        message_id: str | None = None,
    ) -> None:
        if self._artifact_repo is None or not isinstance(paths, list):
            return

        for path in paths:
            if not isinstance(path, str):
                continue
            normalized = normalize_virtual_path(path)
            if not normalized or not is_virtual_user_data_path(normalized):
                continue
            try:
                self._artifact_repo.get_by_conversation_path(conversation_id, normalized)
                continue
            except HTTPException as exc:
                if exc.status_code != 404:
                    raise
            self._artifact_repo.create(
                conversation_id=conversation_id,
                message_id=message_id,
                name=normalized,
                path=normalized,
                artifact_type=artifact_type,
            )

    @staticmethod
    def _native_message_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            if parts:
                return "\n".join(parts)
        if content is None:
            return ""
        return json.dumps(content, ensure_ascii=False)

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

    def _build_runtime(
        self,
        runtime_instance: object,
        runtime_options: ConversationRuntimeOptions,
    ):
        kwargs: dict = {
            "runtime_instance": runtime_instance,
            "default_model": runtime_options.model_name,
            "thinking_enabled": runtime_options.thinking_enabled,
            "subagent_enabled": runtime_options.subagent_enabled,
            "plan_mode": runtime_options.plan_mode,
        }
        return self._runtime_cls(**kwargs)
