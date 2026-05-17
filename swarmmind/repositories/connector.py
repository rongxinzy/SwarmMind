"""Connector repository — CRUD for ConnectorDB with secret-field encryption."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import ConnectorDB
from swarmmind.time_utils import utc_now
from swarmmind.utils.crypto import decrypt, encrypt

# Config keys that contain secrets and must be encrypted at rest
_SECRET_KEYS = {"app_secret", "api_secret", "webhook_secret", "token", "access_token"}


def _encrypt_secrets(config: dict[str, Any]) -> str:
    """Encrypt secret fields in config and return the JSON string."""
    safe: dict[str, Any] = {}
    for key, value in config.items():
        if key in _SECRET_KEYS and isinstance(value, str) and value:
            safe[key] = encrypt(value)
        else:
            safe[key] = value
    return json.dumps(safe, ensure_ascii=False)


def _decrypt_secrets(config_json: str) -> dict[str, Any]:
    """Decrypt secret fields from the stored JSON string."""
    raw: dict[str, Any] = json.loads(config_json) if config_json else {}
    result: dict[str, Any] = {}
    for key, value in raw.items():
        if key in _SECRET_KEYS and isinstance(value, str) and value:
            try:
                result[key] = decrypt(value)
            except Exception:
                result[key] = value  # if decryption fails, return as-is
        else:
            result[key] = value
    return result


def _mask_secrets(config: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of config with secret values masked."""
    return {k: ("***" if k in _SECRET_KEYS and v else v) for k, v in config.items()}


class ConnectorRepository:
    """Repository for connector CRUD operations."""

    def create(
        self,
        connector_id: str | None,
        name: str,
        connector_type: str,
        config: dict[str, Any],
        version: str = "1.0.0",
    ) -> ConnectorDB:
        """Create and persist a new connector.

        Args:
            connector_id: Stable identifier (e.g. ``"feishu-prod"``).
                          Auto-generated if None.
            name: Human-readable label.
            connector_type: Connector type slug (e.g. ``"feishu-cli"``).
            config: Configuration dict; secret fields are encrypted at rest.
            version: Connector version string.

        Returns:
            The persisted ConnectorDB row.
        """
        cid = connector_id or str(uuid.uuid4())
        now = utc_now()
        with session_scope() as session:
            db = ConnectorDB(
                connector_id=cid,
                name=name,
                connector_type=connector_type,
                version=version,
                status="inactive",
                config_json=_encrypt_secrets(config),
                created_at=now,
                updated_at=now,
            )
            session.add(db)
            session.flush()
            session.refresh(db)
            return db

    def list_all(self) -> list[ConnectorDB]:
        """Return all connectors."""
        with session_scope() as session:
            return list(session.exec(select(ConnectorDB)).all())

    def get(self, connector_id: str) -> ConnectorDB | None:
        """Return a connector by ID, or None if not found."""
        with session_scope() as session:
            return session.get(ConnectorDB, connector_id)

    def get_config(self, connector_id: str) -> dict[str, Any]:
        """Return the decrypted config for a connector."""
        db = self.get(connector_id)
        if db is None:
            return {}
        return _decrypt_secrets(db.config_json)

    def get_config_masked(self, connector_id: str) -> dict[str, Any]:
        """Return the config with secret values masked (safe to log/display)."""
        config = self.get_config(connector_id)
        return _mask_secrets(config)

    def update(
        self,
        connector_id: str,
        name: str | None = None,
        config: dict[str, Any] | None = None,
        status: str | None = None,
        mcp_url: str | None = None,
    ) -> ConnectorDB | None:
        """Update connector fields.

        Returns:
            Updated ConnectorDB, or None if the connector was not found.
        """
        with session_scope() as session:
            db = session.get(ConnectorDB, connector_id)
            if db is None:
                return None
            if name is not None:
                db.name = name
            if config is not None:
                # Merge with existing config
                existing = _decrypt_secrets(db.config_json)
                existing.update(config)
                db.config_json = _encrypt_secrets(existing)
            if status is not None:
                db.status = status
            if mcp_url is not None:
                db.mcp_url = mcp_url
            db.updated_at = utc_now()
            session.add(db)
            session.flush()
            session.refresh(db)
            return db

    def record_heartbeat(self, connector_id: str, status: str, mcp_url: str | None) -> ConnectorDB | None:
        """Update heartbeat timestamp and runtime status.

        Returns:
            Updated ConnectorDB, or None if not found.
        """
        with session_scope() as session:
            db = session.get(ConnectorDB, connector_id)
            if db is None:
                return None
            db.status = status
            if mcp_url is not None:
                db.mcp_url = mcp_url
            db.last_heartbeat = utc_now()
            db.updated_at = utc_now()
            session.add(db)
            session.flush()
            session.refresh(db)
            return db

    def delete(self, connector_id: str) -> bool:
        """Delete a connector. Returns True if deleted, False if not found."""
        with session_scope() as session:
            db = session.get(ConnectorDB, connector_id)
            if db is None:
                return False
            session.delete(db)
            return True
