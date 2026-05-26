"""Connector CLI commands."""

from __future__ import annotations

import json
from typing import Annotated, Any

import typer

from swarmmind.cli.commands._common import run_client_command
from swarmmind.cli.config import get_state

connector_app = typer.Typer(help="Manage SwarmMind connectors.", no_args_is_help=True)
feishu_app = typer.Typer(help="Feishu/Lark CLI connector commands.", no_args_is_help=True)
connector_app.add_typer(feishu_app, name="feishu")


# ── Generic connector commands ────────────────────────────────────────────────


@connector_app.command("list")
def list_connectors(ctx: typer.Context) -> None:
    """List all registered connectors."""
    run_client_command(ctx, lambda client: client.list_connectors())


@connector_app.command("get")
def get_connector(
    ctx: typer.Context,
    connector_id: Annotated[str, typer.Argument(help="Connector ID.")],
) -> None:
    """Show details for a connector (secrets masked)."""
    run_client_command(ctx, lambda client: client.get_connector(connector_id))


@connector_app.command("add")
def add_connector(
    ctx: typer.Context,
    connector_type: Annotated[str, typer.Argument(help="Connector type (e.g. feishu-cli).")],
    connector_id: Annotated[str | None, typer.Option("--id", help="Stable connector ID.")] = None,
    name: Annotated[str | None, typer.Option("--name", help="Human-readable label.")] = None,
    config: Annotated[str | None, typer.Option("--config", help="Config as a JSON string.")] = None,
) -> None:
    """Register a new connector.

    Example:
        swarmmind connector add feishu-cli --id feishu-prod --config '{"bot_name":"SwarmBot"}'
    """
    parsed_config: dict[str, Any] = {}
    if config:
        try:
            parsed_config = json.loads(config)
        except json.JSONDecodeError as exc:
            typer.echo(f"Error: --config is not valid JSON: {exc}", err=True)
            raise typer.Exit(2) from exc

    display_name = name or connector_type
    run_client_command(
        ctx,
        lambda client: client.create_connector(
            connector_type=connector_type,
            connector_id=connector_id,
            name=display_name,
            config=parsed_config,
        ),
    )


@connector_app.command("update")
def update_connector(
    ctx: typer.Context,
    connector_id: Annotated[str, typer.Argument(help="Connector ID.")],
    name: Annotated[str | None, typer.Option("--name")] = None,
    config: Annotated[str | None, typer.Option("--config", help="Partial config as JSON.")] = None,
) -> None:
    """Update connector name or configuration."""
    parsed_config: dict[str, Any] | None = None
    if config:
        try:
            parsed_config = json.loads(config)
        except json.JSONDecodeError as exc:
            typer.echo(f"Error: --config is not valid JSON: {exc}", err=True)
            raise typer.Exit(2) from exc

    run_client_command(
        ctx,
        lambda client: client.update_connector(connector_id, name=name, config=parsed_config),
    )


@connector_app.command("remove")
def remove_connector(
    ctx: typer.Context,
    connector_id: Annotated[str, typer.Argument(help="Connector ID.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt.")] = False,
) -> None:
    """Remove a connector registration."""
    if not yes:
        confirmed = typer.confirm(f"Remove connector '{connector_id}'?")
        if not confirmed:
            raise typer.Exit(0)
    run_client_command(ctx, lambda client: client.delete_connector(connector_id))


@connector_app.command("status")
def connector_status(
    ctx: typer.Context,
    connector_id: Annotated[str, typer.Argument(help="Connector ID.")],
) -> None:
    """Show the runtime status of a connector."""
    run_client_command(ctx, lambda client: client.get_connector(connector_id))


@connector_app.command("types")
def list_connector_types(ctx: typer.Context) -> None:
    """List all available connector types and their configuration schemas."""
    run_client_command(ctx, lambda client: client.list_connector_types())


# ── Feishu-specific commands ──────────────────────────────────────────────────


@feishu_app.command("serve-tools")
def feishu_serve_tools(
    ctx: typer.Context,
    connector_id: Annotated[str | None, typer.Option("--id", help="Connector ID to load config from.")] = None,
    port: Annotated[int, typer.Option("--port", help="MCP server port.")] = 7070,
) -> None:
    """Start the Feishu MCP tool server for DeerFlow agents.

    The server exposes lark-cli commands as MCP tools on:
        http://0.0.0.0:<port>/mcp

    Add this URL to your RuntimeProfile's mcp_servers configuration so
    DeerFlow agents can call Feishu APIs directly.

    Prerequisites:
        npx @larksuite/cli@latest install
        lark-cli config init
        lark-cli auth login --recommend
    """
    from swarmmind.connectors.feishu.connector import FeishuCLIConnector

    state = get_state(ctx)
    config: dict[str, Any] = {}

    if connector_id:
        # Load config from SwarmMind API
        from swarmmind.cli.client import SwarmMindClient

        try:
            with SwarmMindClient(api_url=state.api_url, api_token=state.api_token) as client:
                resp = client._request("GET", f"/connectors/{connector_id}")
                config = resp.get("config", {}) if isinstance(resp, dict) else {}
        except Exception as exc:
            typer.echo(f"Warning: could not load connector config: {exc}", err=True)

    typer.echo(f"Starting Feishu MCP tool server on port {port}...")
    typer.echo(f"  MCP URL: http://0.0.0.0:{port}/mcp")
    typer.echo("  Add this to your RuntimeProfile mcp_servers to enable Feishu tools for agents.")
    typer.echo("  Press Ctrl+C to stop.")

    connector = FeishuCLIConnector()
    connector.run_tool_server_sync(config, port=port)


@feishu_app.command("listen-events")
def feishu_listen_events(
    ctx: typer.Context,
    connector_id: Annotated[str | None, typer.Option("--id", help="Connector ID to load config from.")] = None,
    bot_name: Annotated[str, typer.Option("--bot-name", help="Bot display name for @mention filtering.")] = "",
    project_id: Annotated[str | None, typer.Option("--project-id", help="Default SwarmMind project ID.")] = None,
) -> None:
    """Start the Feishu event listener (bot messages → SwarmMind dispatch).

    Runs lark-cli event +listen and routes inbound Feishu messages to
    SwarmMind conversations or dispatch. Replies are posted back to Feishu.

    Prerequisites:
        lark-cli config init
        lark-cli auth login --domain im
        lark-cli event setup   # configure bot webhook
    """
    from swarmmind.connectors.feishu.connector import FeishuCLIConnector

    state = get_state(ctx)
    config: dict[str, Any] = {}

    if connector_id:
        from swarmmind.cli.client import SwarmMindClient

        try:
            with SwarmMindClient(api_url=state.api_url, api_token=state.api_token) as client:
                resp = client._request("GET", f"/connectors/{connector_id}")
                config = resp.get("config", {}) if isinstance(resp, dict) else {}
        except Exception as exc:
            typer.echo(f"Warning: could not load connector config: {exc}", err=True)

    if bot_name:
        config["bot_name"] = bot_name
    if project_id:
        config["default_project_id"] = project_id

    typer.echo("Starting Feishu event listener...")
    typer.echo(f"  SwarmMind API: {state.api_url}")
    if config.get("bot_name"):
        typer.echo(f"  Bot name filter: @{config['bot_name']}")
    if config.get("default_project_id"):
        typer.echo(f"  Default project: {config['default_project_id']}")
    typer.echo("  Press Ctrl+C to stop.")

    connector = FeishuCLIConnector()
    connector.run_event_listener_sync(config, api_url=state.api_url, api_token=state.api_token)


@feishu_app.command("health")
def feishu_health(ctx: typer.Context) -> None:
    """Check if lark-cli is installed and accessible."""
    from swarmmind.connectors.feishu.connector import FeishuCLIConnector

    state = get_state(ctx)
    connector = FeishuCLIConnector()
    result = connector.health()
    if state.json_output:
        typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = result.get("status", "unknown")
        if status == "ok":
            typer.echo(f"✓ lark-cli found at {result.get('lark_cli_path', 'unknown')}")
        else:
            typer.echo(f"✗ {result.get('reason', 'lark-cli not available')}", err=True)
            raise typer.Exit(1)
