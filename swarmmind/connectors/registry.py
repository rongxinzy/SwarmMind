"""Connector type registry — single source of truth for available connector types.

The registry is code-level (not persisted): connector types ship with the
codebase, connector *instances* live in ConnectorDB.

Usage::

    from swarmmind.connectors.registry import REGISTRY

    manifest = REGISTRY.get_manifest("feishu-cli")  # or None
    all_types = REGISTRY.list_manifests()
    REGISTRY.is_registered("feishu-cli")  # bool
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from swarmmind.connectors.base import BaseConnector, ConnectorManifest


@dataclass(frozen=True)
class ConnectorEntry:
    """A registered connector type with its class and manifest."""

    connector_class: type[BaseConnector]
    manifest: ConnectorManifest


class ConnectorRegistry:
    """Immutable registry of connector types available in this installation."""

    def __init__(self) -> None:
        self._entries: dict[str, ConnectorEntry] = {}

    def register(
        self,
        connector_type: str,
        connector_class: type[BaseConnector],
        manifest: ConnectorManifest,
    ) -> None:
        """Register a connector type.

        Args:
            connector_type: Stable slug (e.g. ``"feishu-cli"``).
            connector_class: Concrete ``BaseConnector`` subclass.
            manifest: Static ``ConnectorManifest`` instance.
        """
        self._entries[connector_type] = ConnectorEntry(
            connector_class=connector_class,
            manifest=manifest,
        )

    def get_entry(self, connector_type: str) -> ConnectorEntry | None:
        """Return the ConnectorEntry for *connector_type*, or None if unknown."""
        return self._entries.get(connector_type)

    def get_manifest(self, connector_type: str) -> ConnectorManifest | None:
        """Return the manifest for *connector_type*, or None if unknown."""
        entry = self._entries.get(connector_type)
        return entry.manifest if entry else None

    def get_class(self, connector_type: str) -> type[BaseConnector] | None:
        """Return the connector class for *connector_type*, or None if unknown."""
        entry = self._entries.get(connector_type)
        return entry.connector_class if entry else None

    def is_registered(self, connector_type: str) -> bool:
        """Return True if *connector_type* is registered."""
        return connector_type in self._entries

    def list_manifests(self) -> list[ConnectorManifest]:
        """Return all registered manifests, sorted by name."""
        return sorted(
            (e.manifest for e in self._entries.values()),
            key=lambda m: m.name,
        )

    def list_types(self) -> list[str]:
        """Return all registered connector type slugs, sorted."""
        return sorted(self._entries.keys())


# ---------------------------------------------------------------------------
# Module-level singleton — the only registry instance in the process.
# ---------------------------------------------------------------------------
REGISTRY = ConnectorRegistry()


def _bootstrap() -> None:
    """Register all built-in connector types.

    This is called once at module import. Adding a new connector type only
    requires adding an entry here and shipping the implementation.
    """
    from swarmmind.connectors.feishu.connector import FeishuCLIConnector
    from swarmmind.connectors.feishu.manifest import FEISHU_CLI_MANIFEST

    REGISTRY.register(
        connector_type="feishu-cli",
        connector_class=FeishuCLIConnector,
        manifest=FEISHU_CLI_MANIFEST,
    )


_bootstrap()
