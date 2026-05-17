"""Feishu CLI connector manifest."""

from __future__ import annotations

from swarmmind.connectors.base import (
    ConnectorCapability,
    ConnectorConfigField,
    ConnectorManifest,
    ConnectorTransport,
)

FEISHU_CLI_MANIFEST = ConnectorManifest(
    name="feishu-cli",
    version="1.0.0",
    description=(
        "Bridges Feishu/Lark to SwarmMind via the official lark-cli tool. "
        "Exposes 200+ Feishu commands as MCP tools for agents, and can ingest "
        "Feishu bot events (messages, @mentions) into SwarmMind conversations."
    ),
    capabilities=[ConnectorCapability.INGEST, ConnectorCapability.TOOL_PROVIDER],
    transport=ConnectorTransport.MCP_HTTP,
    config_schema=[
        ConnectorConfigField(
            name="app_id",
            description="Feishu app ID from the Feishu Open Platform developer console.",
            required=False,
            secret=False,
        ),
        ConnectorConfigField(
            name="app_secret",
            description="Feishu app secret. Stored encrypted at rest.",
            required=False,
            secret=True,
        ),
        ConnectorConfigField(
            name="mcp_port",
            description="TCP port for the MCP tool server.",
            required=False,
            secret=False,
            default="7070",
        ),
        ConnectorConfigField(
            name="bot_name",
            description=(
                "Display name of the Feishu bot. Used to filter @mentions in group chats. "
                "Leave empty to process all messages the bot receives."
            ),
            required=False,
            secret=False,
            default="",
        ),
        ConnectorConfigField(
            name="default_project_id",
            description=(
                "SwarmMind project ID to associate inbound Feishu messages with. "
                "Leave empty to route via dispatch (no fixed project)."
            ),
            required=False,
            secret=False,
            default="",
        ),
    ],
)
