"""MCP server commands."""

from __future__ import annotations

import typer

from swarmmind.cli.config import get_state

mcp_app = typer.Typer(help="Expose SwarmMind CLI capabilities over MCP.", no_args_is_help=True)


@mcp_app.command("serve")
def serve_mcp(ctx: typer.Context) -> None:
    state = get_state(ctx)
    from swarmmind.cli.mcp_server import build_mcp_server

    server = build_mcp_server(api_url=state.api_url)
    server.run(transport="stdio")
