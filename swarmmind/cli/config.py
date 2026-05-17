"""CLI configuration and context helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass

import typer

DEFAULT_API_URL = "http://127.0.0.1:8000"
API_URL_ENV = "SWARMMIND_API_URL"
API_TOKEN_ENV = "SWARMMIND_API_TOKEN"  # noqa: S105 - environment variable name, not a token value.


@dataclass
class CLIState:
    """Resolved root CLI state shared by commands."""

    api_url: str
    api_token: str | None = None
    json_output: bool = False
    quiet: bool = False


def resolve_api_url(api_url: str | None = None) -> str:
    """Resolve API URL from flag, environment, then local default."""
    resolved = api_url or os.environ.get(API_URL_ENV) or DEFAULT_API_URL
    return resolved.rstrip("/")


def resolve_api_token(api_token: str | None = None) -> str | None:
    """Resolve bearer token from flag, environment, then no token."""
    return api_token or os.environ.get(API_TOKEN_ENV)


def get_state(ctx: typer.Context) -> CLIState:
    """Return the current CLI state from Typer context."""
    if isinstance(ctx.obj, CLIState):
        return ctx.obj
    state = CLIState(api_url=resolve_api_url(), api_token=resolve_api_token())
    ctx.obj = state
    return state


def get_client(ctx: typer.Context):
    """Create an HTTP client for the current CLI invocation."""
    from swarmmind.cli.client import SwarmMindClient

    state = get_state(ctx)
    return SwarmMindClient(api_url=state.api_url, api_token=state.api_token)
