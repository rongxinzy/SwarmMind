"""SwarmMind connector framework.

A connector is a bidirectional integration unit that bridges an external system
to the SwarmMind control plane:

- **Ingress**: external events → SwarmMind dispatch / conversation
- **Tool Provider**: SwarmMind agents → external APIs via MCP tools
"""

from swarmmind.connectors.base import BaseConnector, ConnectorCapability, ConnectorManifest, ConnectorTransport

__all__ = ["BaseConnector", "ConnectorCapability", "ConnectorManifest", "ConnectorTransport"]
