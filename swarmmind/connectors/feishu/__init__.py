"""Feishu/Lark CLI connector for SwarmMind.

Bridges Feishu to SwarmMind via the official lark-cli tool:
- MCP tool server: exposes lark-cli commands as MCP tools for DeerFlow agents
- Event listener: receives Feishu bot events and dispatches to SwarmMind

Prerequisites:
    lark-cli must be installed and authenticated:
        npx @larksuite/cli@latest install
        lark-cli config init   # configure app_id / app_secret
        lark-cli auth login --recommend
"""

from swarmmind.connectors.feishu.connector import FeishuCLIConnector

__all__ = ["FeishuCLIConnector"]
