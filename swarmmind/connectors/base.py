"""Base connector interface for SwarmMind."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel


class ConnectorCapability(str, Enum):
    """What a connector can do."""

    INGEST = "ingest"
    EGRESS = "egress"
    TOOL_PROVIDER = "tool_provider"


class ConnectorTransport(str, Enum):
    """How the connector's tool interface is exposed."""

    MCP_STDIO = "mcp_stdio"
    MCP_HTTP = "mcp_http"
    CLI = "cli"
    WEBHOOK = "webhook"


class ConnectorConfigField(BaseModel):
    """A single configuration field in a connector manifest."""

    name: str
    description: str
    required: bool = True
    secret: bool = False
    default: str | None = None


class ConnectorManifest(BaseModel):
    """Static descriptor for a connector type — declared by each connector implementation."""

    name: str
    version: str
    description: str
    capabilities: list[ConnectorCapability]
    transport: ConnectorTransport
    config_schema: list[ConnectorConfigField] = []


class BaseConnector(ABC):
    """Abstract base for all SwarmMind connectors.

    Concrete connectors implement this interface and are executed as independent
    processes that call SwarmMind's REST API. They are never embedded in the API
    server process.
    """

    @property
    @abstractmethod
    def manifest(self) -> ConnectorManifest:
        """Static manifest describing this connector's capabilities."""

    @abstractmethod
    async def start_tool_server(self, config: dict[str, Any], port: int) -> None:
        """Start the MCP tool server that exposes external system APIs to agents."""

    @abstractmethod
    async def start_event_listener(self, config: dict[str, Any], api_url: str, api_token: str | None) -> None:
        """Start the event listener that ingests external events into SwarmMind."""

    @abstractmethod
    def health(self) -> dict[str, Any]:
        """Return current health status."""
