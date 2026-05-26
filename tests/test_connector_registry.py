"""Tests for ConnectorRegistry and config validation."""

from __future__ import annotations

from swarmmind.connectors.base import (
    ConnectorCapability,
    ConnectorConfigField,
    ConnectorManifest,
    ConnectorTransport,
)
from swarmmind.connectors.config_validation import validate_config
from swarmmind.connectors.registry import REGISTRY, ConnectorRegistry

# ── Registry unit tests ───────────────────────────────────────────────────────


def test_registry_has_feishu_cli():
    assert REGISTRY.is_registered("feishu-cli")


def test_registry_get_manifest_returns_manifest():
    manifest = REGISTRY.get_manifest("feishu-cli")
    assert manifest is not None
    assert manifest.name == "feishu-cli"


def test_registry_get_manifest_unknown_returns_none():
    assert REGISTRY.get_manifest("nonexistent-connector") is None


def test_registry_is_registered_unknown_returns_false():
    assert REGISTRY.is_registered("totally-unknown") is False


def test_registry_list_manifests_nonempty():
    manifests = REGISTRY.list_manifests()
    assert len(manifests) >= 1
    names = [m.name for m in manifests]
    assert "feishu-cli" in names


def test_registry_list_types_sorted():
    types = REGISTRY.list_types()
    assert types == sorted(types)
    assert "feishu-cli" in types


def test_registry_get_class_returns_class():
    cls = REGISTRY.get_class("feishu-cli")
    assert cls is not None


def test_registry_get_class_unknown_returns_none():
    assert REGISTRY.get_class("ghost") is None


def test_custom_registry_register_and_lookup():
    """A fresh registry can register and look up entries independently."""
    from swarmmind.connectors.feishu.connector import FeishuCLIConnector
    from swarmmind.connectors.feishu.manifest import FEISHU_CLI_MANIFEST

    reg = ConnectorRegistry()
    assert not reg.is_registered("feishu-cli")

    reg.register("feishu-cli", FeishuCLIConnector, FEISHU_CLI_MANIFEST)
    assert reg.is_registered("feishu-cli")
    assert reg.get_manifest("feishu-cli") is FEISHU_CLI_MANIFEST


# ── Config validation unit tests ─────────────────────────────────────────────


def _make_manifest(fields: list[ConnectorConfigField]) -> ConnectorManifest:
    return ConnectorManifest(
        name="test-connector",
        version="1.0.0",
        description="Test connector",
        capabilities=[ConnectorCapability.INGEST],
        transport=ConnectorTransport.MCP_HTTP,
        config_schema=fields,
    )


def test_validate_config_empty_schema_empty_config():
    manifest = _make_manifest([])
    assert validate_config(manifest, {}) == []


def test_validate_config_valid_all_fields():
    manifest = _make_manifest([
        ConnectorConfigField(name="api_key", description="Key", required=True, secret=True),
        ConnectorConfigField(name="base_url", description="URL", required=False),
    ])
    errors = validate_config(manifest, {"api_key": "secret", "base_url": "http://x"})
    assert errors == []


def test_validate_config_missing_required_field():
    manifest = _make_manifest([
        ConnectorConfigField(name="api_key", description="Key", required=True, secret=True),
    ])
    errors = validate_config(manifest, {})
    assert len(errors) == 1
    assert errors[0]["field"] == "api_key"


def test_validate_config_empty_string_required_field():
    manifest = _make_manifest([
        ConnectorConfigField(name="api_key", description="Key", required=True, secret=True),
    ])
    errors = validate_config(manifest, {"api_key": "  "})
    assert len(errors) == 1
    assert errors[0]["field"] == "api_key"


def test_validate_config_unknown_field_rejected():
    manifest = _make_manifest([
        ConnectorConfigField(name="base_url", description="URL", required=False),
    ])
    errors = validate_config(manifest, {"base_url": "http://x", "secret_sauce": "nope"})
    assert len(errors) == 1
    assert errors[0]["field"] == "secret_sauce"


def test_validate_config_optional_field_absent_is_ok():
    manifest = _make_manifest([
        ConnectorConfigField(name="base_url", description="URL", required=False),
    ])
    assert validate_config(manifest, {}) == []


def test_validate_config_multiple_errors():
    manifest = _make_manifest([
        ConnectorConfigField(name="req1", description="R1", required=True),
        ConnectorConfigField(name="req2", description="R2", required=True),
    ])
    errors = validate_config(manifest, {"unknown_key": "val"})
    field_names = {e["field"] for e in errors}
    assert "req1" in field_names
    assert "req2" in field_names
    assert "unknown_key" in field_names


# ── API integration: /connectors/types ───────────────────────────────────────


def test_connector_types_api_shape():
    """GET /connectors/types returns ConnectorTypesResponse-compatible shape."""
    from fastapi.testclient import TestClient

    from swarmmind.api.routers.connectors import router

    app_tmp = __import__("fastapi", fromlist=["FastAPI"]).FastAPI()
    app_tmp.include_router(router)
    client = TestClient(app_tmp)

    resp = client.get("/connectors/types")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1

    feishu = next((i for i in data["items"] if i["name"] == "feishu-cli"), None)
    assert feishu is not None
    assert "config_schema" in feishu
    assert "capabilities" in feishu
    assert "transport" in feishu


def test_connector_create_unknown_type_rejected():
    """POST /connectors with an unknown connector_type returns HTTP 422."""
    from fastapi.testclient import TestClient

    from swarmmind.api.routers.connectors import router

    app_tmp = __import__("fastapi", fromlist=["FastAPI"]).FastAPI()
    app_tmp.include_router(router)
    client = TestClient(app_tmp)

    resp = client.post(
        "/connectors",
        json={"name": "test", "connector_type": "ghost-connector", "config": {}},
    )
    assert resp.status_code == 422
    assert "ghost-connector" in resp.text
