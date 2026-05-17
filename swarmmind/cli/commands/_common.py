"""Shared command helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import Any

import typer
from pydantic import ValidationError

from swarmmind.cli.client import ParameterError, SwarmMindCLIError
from swarmmind.cli.config import get_client, get_state
from swarmmind.cli.output import render_error, render_result, render_stream_event


def run_client_command(ctx: typer.Context, fn: Callable[[Any], Any]) -> None:
    """Run a client command with normalized errors and output."""
    state = get_state(ctx)
    try:
        with get_client(ctx) as client:
            result = fn(client)
    except ValidationError as exc:
        normalized = ParameterError(str(exc))
        render_error(normalized, json_output=state.json_output, quiet=state.quiet)
        raise typer.Exit(normalized.exit_code) from exc
    except SwarmMindCLIError as exc:
        render_error(exc, json_output=state.json_output, quiet=state.quiet)
        raise typer.Exit(exc.exit_code) from exc
    render_result(result, json_output=state.json_output, quiet=state.quiet)


def run_stream_command(ctx: typer.Context, events_fn: Callable[[Any], Iterable[dict[str, Any]]]) -> None:
    """Run a stream command and render each event as it arrives."""
    state = get_state(ctx)
    try:
        with get_client(ctx) as client:
            for event in events_fn(client):
                render_stream_event(event, json_output=state.json_output)
    except ValidationError as exc:
        normalized = ParameterError(str(exc))
        render_error(normalized, json_output=state.json_output, quiet=state.quiet)
        raise typer.Exit(normalized.exit_code) from exc
    except SwarmMindCLIError as exc:
        render_error(exc, json_output=state.json_output, quiet=state.quiet)
        raise typer.Exit(exc.exit_code) from exc


def joined_message(parts: Sequence[str]) -> str:
    """Join variadic message parts into the final message text."""
    return " ".join(parts).strip()


def split_csv(value: str | None) -> list[str] | None:
    """Parse a comma-separated option into a list."""
    if value is None:
        return None
    parts = [item.strip() for item in value.split(",") if item.strip()]
    return parts or None
