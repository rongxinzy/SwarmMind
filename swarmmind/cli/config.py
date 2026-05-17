"""CLI configuration and context helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass

import typer

DEFAULT_API_URL = "http://127.0.0.1:8000"
API_URL_ENV = "SWARMMIND_API_URL"


@dataclass
class CLIState:
    """Resolved root CLI state shared by commands."""

    api_url: str
    json_output: bool = False
    quiet: bool = False


def resolve_api_url(api_url: str | None = None) -> str:
    """Resolve API URL from flag, environment, then local default."""
    resolved = api_url or os.environ.get(API_URL_ENV) or DEFAULT_API_URL
    return resolved.rstrip("/")


def get_state(ctx: typer.Context) -> CLIState:
    """Return the current CLI state from Typer context."""
    if isinstance(ctx.obj, CLIState):
        return ctx.obj
    state = CLIState(api_url=resolve_api_url())
    ctx.obj = state
    return state


def get_client(ctx: typer.Context):
    """Create an HTTP client for the current CLI invocation."""
    from swarmmind.cli.client import SwarmMindClient

    return SwarmMindClient(api_url=get_state(ctx).api_url)
