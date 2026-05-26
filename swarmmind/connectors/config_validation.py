"""Connector config validation against a ConnectorManifest schema.

Validates that a supplied config dict satisfies the manifest's field rules:
- Required fields are present and non-empty.
- No unknown fields are present.
- Returns field-level errors so the API can surface them as HTTP 422 details.

Usage::

    from swarmmind.connectors.config_validation import validate_config
    from swarmmind.connectors.registry import REGISTRY

    manifest = REGISTRY.get_manifest("feishu-cli")
    errors = validate_config(manifest, {"app_id": "x"})
    # errors is empty → config is valid
"""

from __future__ import annotations

from typing import Any

from swarmmind.connectors.base import ConnectorManifest


def validate_config(
    manifest: ConnectorManifest,
    config: dict[str, Any],
) -> list[dict[str, str]]:
    """Validate *config* against *manifest*.config_schema.

    Args:
        manifest: The ConnectorManifest whose ``config_schema`` defines the rules.
        config: The user-supplied config dict to validate.

    Returns:
        A list of ``{"field": ..., "error": ...}`` dicts. Empty means valid.
    """
    errors: list[dict[str, str]] = []

    known_fields = {field.name for field in manifest.config_schema}
    required_fields = {field.name for field in manifest.config_schema if field.required}

    # Check for unknown keys
    errors = [
        {"field": key, "error": f"Unknown field '{key}' for connector type '{manifest.name}'."}
        for key in config
        if key not in known_fields
    ]

    # Check for required fields that are missing or empty
    for field_name in required_fields:
        value = config.get(field_name)
        if value is None or (isinstance(value, str) and not value.strip()):
            errors.append({"field": field_name, "error": f"Required field '{field_name}' is missing or empty."})

    return errors
