"""MCP stdio server wrapping SwarmMind CLI client capabilities."""

from __future__ import annotations

from typing import Any

from swarmmind.cli.output import to_data


def build_mcp_server(api_url: str):
    """Build a FastMCP server for SwarmMind HTTP capabilities."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ModuleNotFoundError as exc:
        raise RuntimeError("MCP support is not installed. Install with `pip install 'swarmmind[mcp]'`.") from exc

    from swarmmind.cli.client import SwarmMindClient

    mcp = FastMCP("swarmmind")

    def _client_call(fn):
        with SwarmMindClient(api_url=api_url) as client:
            return to_data(fn(client))

    @mcp.tool()
    def health() -> dict[str, Any]:
        """Check SwarmMind supervisor API health."""
        return _client_call(lambda client: client.health())

    @mcp.tool()
    def dispatch(goal: str) -> dict[str, Any]:
        """Dispatch a goal through the SwarmMind supervisor router."""
        return _client_call(lambda client: client.dispatch(goal))

    @mcp.tool()
    def conversation_create(title: str | None = None) -> dict[str, Any]:
        """Create a ChatSession."""
        return _client_call(lambda client: client.create_conversation(title=title))

    @mcp.tool()
    def chat_send(conversation_id: str, message: str, mode: str | None = None) -> dict[str, Any]:
        """Send a non-streaming ChatSession message."""
        return _client_call(lambda client: client.send_message(conversation_id, message, mode=mode))

    @mcp.tool()
    def project_list() -> dict[str, Any]:
        """List governed projects."""
        return _client_call(lambda client: client.list_projects())

    @mcp.tool()
    def project_create(title: str, goal: str | None = None) -> dict[str, Any]:
        """Create a governed project."""
        return _client_call(lambda client: client.create_project(title=title, goal=goal))

    @mcp.tool()
    def memory_get(key: str, layer: str, scope_id: str) -> dict[str, Any]:
        """Read one layered-memory entry."""
        return _client_call(lambda client: client.get_memory(key, layer=layer, scope_id=scope_id))

    return mcp
