"""CLI output renderers for human, JSON, and stream modes."""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

import typer
from pydantic import BaseModel

from swarmmind.cli.client import SwarmMindCLIError


def to_data(value: Any) -> Any:
    """Convert Pydantic and enum values into JSON-serializable data."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [to_data(v) for v in value]
    if isinstance(value, tuple):
        return [to_data(v) for v in value]
    if isinstance(value, dict):
        return {k: to_data(v) for k, v in value.items()}
    return value


def render_result(value: Any, *, json_output: bool, quiet: bool = False) -> None:
    """Render a command result to stdout."""
    if quiet:
        return
    data = to_data(value)
    if json_output:
        typer.echo(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
        return
    typer.echo(render_human(data))


def render_error(error: SwarmMindCLIError, *, json_output: bool, quiet: bool = False) -> None:
    """Render a normalized CLI error to stderr."""
    if quiet:
        return
    if json_output:
        typer.echo(
            json.dumps(
                {
                    "error": error.message,
                    "exit_code": error.exit_code,
                    "status_code": error.status_code,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            err=True,
        )
        return
    typer.echo(f"error: {error.message}", err=True)


def render_human(data: Any) -> str:
    """Render JSON-like data in a compact human-readable form."""
    if data is None:
        return "no content"
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        return "\n".join(_summarize_item(item) for item in data) if data else "no items"
    if isinstance(data, dict):
        if "items" in data and isinstance(data["items"], list):
            lines = [f"total: {data.get('total', len(data['items']))}"]
            lines.extend(_summarize_item(item) for item in data["items"])
            return "\n".join(lines)
        return "\n".join(f"{key}: {_short(value)}" for key, value in data.items())
    return str(data)


def render_stream_event(event: dict[str, Any], *, json_output: bool) -> None:
    """Render one streaming event."""
    if json_output:
        typer.echo(json.dumps(to_data(event), ensure_ascii=False, separators=(",", ":")))
        return
    text = stream_event_text(event)
    if text:
        typer.echo(text)


def stream_event_text(event: dict[str, Any]) -> str | None:
    """Return a human-readable line for a stream event."""
    event_type = event.get("type")
    if event_type == "status":
        return _first_text(event, "label", "phase")
    if event_type in {"status.thinking", "status.running"}:
        return _first_text(event, "text", "label")
    if event_type == "status.plan_steps":
        steps = event.get("steps") or []
        descriptions = [s.get("description") for s in steps if isinstance(s, dict) and s.get("description")]
        return "plan: " + " | ".join(descriptions) if descriptions else None
    if event_type == "status.artifact":
        return f"artifact: {_first_text(event, 'name', 'artifact_type')}"
    if event_type == "status.clarification":
        return f"clarification: {_first_text(event, 'question')}"
    if event_type == "status.waiting_approval":
        return f"waiting approval: {_first_text(event, 'title', 'approval_id', 'requested_capability')}"
    if event_type == "content.accumulated":
        return str(event.get("text") or "")
    if event_type == "assistant_final":
        message = event.get("message")
        if isinstance(message, dict):
            return str(message.get("content") or "")
        return None
    if event_type == "user_message":
        return None
    if event_type in {"task_started", "task_running", "task_completed", "task_failed"}:
        task = event.get("task")
        if isinstance(task, dict):
            return f"{event_type}: {_first_text(task, 'description', 'message', 'result', 'error', 'id')}"
    if event_type == "team_activity":
        activity = event.get("activity")
        if isinstance(activity, dict):
            label = _first_text(activity, "label", "detail")
            detail = activity.get("detail")
            return f"{label}: {detail}" if label and detail and label != detail else label
    if event_type == "title":
        conversation = event.get("conversation")
        if isinstance(conversation, dict):
            return f"title: {conversation.get('title')}"
    if event_type == "error":
        return f"error: {_first_text(event, 'message', 'code')}"
    if event_type == "done":
        return "done"
    if event_type == "raw":
        return str(event.get("text") or event.get("data") or "")
    return None


def _summarize_item(item: Any) -> str:
    if not isinstance(item, dict):
        return _short(item)
    for fields in (
        ("project_id", "title", "status"),
        ("id", "title", "updated_at"),
        ("run_id", "status", "goal"),
        ("task_id", "title", "status"),
        ("approval_id", "title", "status"),
        ("audit_id", "audit_type", "decision"),
        ("key", "value", "version"),
        ("agent_id", "status", "action_proposal_id"),
    ):
        present = [(field, item.get(field)) for field in fields if item.get(field) is not None]
        if present:
            return "  " + " | ".join(f"{field}={_short(value)}" for field, value in present)
    return "  " + json.dumps(item, ensure_ascii=False, default=str)


def _short(value: Any, max_len: int = 140) -> str:
    data = to_data(value)
    if isinstance(data, (dict, list)):
        text = json.dumps(data, ensure_ascii=False, default=str)
    else:
        text = str(data)
    text = text.replace("\n", "\\n")
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _first_text(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if value is not None:
            return _short(value)
    return ""
