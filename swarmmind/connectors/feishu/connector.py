"""Feishu CLI connector — orchestrates MCP bridge and event listener."""

from __future__ import annotations

import asyncio
from typing import Any

from swarmmind.connectors.base import BaseConnector, ConnectorManifest
from swarmmind.connectors.feishu.manifest import FEISHU_CLI_MANIFEST


class FeishuCLIConnector(BaseConnector):
    """Feishu/Lark connector via the official lark-cli tool.

    Provides two modes of operation:
    - **Tool server**: FastMCP server exposing lark-cli commands as MCP tools
      for DeerFlow agents (``start_tool_server``).
    - **Event listener**: Long-running process that ingests Feishu bot events
      and dispatches them to SwarmMind (``start_event_listener``).

    Both modes require ``lark-cli`` to be installed and authenticated:
        npx @larksuite/cli@latest install
        lark-cli config init
        lark-cli auth login --recommend
    """

    @property
    def manifest(self) -> ConnectorManifest:
        """Return the Feishu CLI connector manifest."""
        return FEISHU_CLI_MANIFEST

    async def start_tool_server(self, config: dict[str, Any], port: int = 7070) -> None:
        """Start the MCP tool server on the given port.

        Args:
            config: Connector configuration (currently unused; lark-cli manages its own auth).
            port: TCP port to bind (default 7070).
        """
        from swarmmind.connectors.feishu.mcp_bridge import build_feishu_mcp_server

        mcp = build_feishu_mcp_server(port=port)
        # FastMCP.run_async with streamable-http transport
        await mcp.run_async(transport="streamable-http", host="0.0.0.0", port=port)  # noqa: S104

    async def start_event_listener(
        self,
        config: dict[str, Any],
        api_url: str,
        api_token: str | None = None,
    ) -> None:
        """Start the Feishu event listener.

        Args:
            config: Connector configuration dict. Recognized keys:
                ``bot_name``, ``default_project_id``.
            api_url: SwarmMind supervisor API base URL.
            api_token: Bearer token for the SwarmMind API (optional).
        """
        from swarmmind.connectors.feishu.event_listener import FeishuEventListener

        listener = FeishuEventListener(
            api_url=api_url,
            api_token=api_token,
            bot_name=config.get("bot_name", ""),
            default_project_id=config.get("default_project_id", ""),
        )
        await listener.run()

    def health(self) -> dict[str, Any]:
        """Return health status by checking lark-cli availability."""
        from swarmmind.connectors.feishu.cli_runner import LarkCLINotFoundError, check_lark_cli

        try:
            path = check_lark_cli()
            return {"status": "ok", "lark_cli_path": path}
        except LarkCLINotFoundError as exc:
            return {"status": "error", "reason": str(exc)}

    def run_tool_server_sync(self, config: dict[str, Any], port: int = 7070) -> None:
        """Synchronous entry point for the tool server (used by CLI commands)."""
        asyncio.run(self.start_tool_server(config, port=port))

    def run_event_listener_sync(
        self,
        config: dict[str, Any],
        api_url: str,
        api_token: str | None = None,
    ) -> None:
        """Synchronous entry point for the event listener (used by CLI commands)."""
        asyncio.run(self.start_event_listener(config, api_url=api_url, api_token=api_token))
