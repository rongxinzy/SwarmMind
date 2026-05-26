"""REST API endpoints for connector management."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from swarmmind.connectors.config_validation import validate_config
from swarmmind.connectors.registry import REGISTRY
from swarmmind.models import (
    ConnectorConfigFieldInfo,
    ConnectorCreateRequest,
    ConnectorHeartbeatRequest,
    ConnectorListResponse,
    ConnectorResponse,
    ConnectorTypeInfo,
    ConnectorTypesResponse,
    ConnectorUpdateRequest,
    DeleteConnectorResponse,
)
from swarmmind.repositories.connector import ConnectorRepository

router = APIRouter(prefix="/connectors", tags=["connectors"])

_repo = ConnectorRepository()


def _to_response(db: Any) -> ConnectorResponse:
    """Convert ConnectorDB row to ConnectorResponse with masked secrets."""
    return ConnectorResponse(
        connector_id=db.connector_id,
        name=db.name,
        connector_type=db.connector_type,
        version=db.version,
        status=db.status,
        config=_repo.get_config_masked(db.connector_id),
        mcp_url=db.mcp_url,
        last_heartbeat=db.last_heartbeat,
        created_at=db.created_at,
        updated_at=db.updated_at,
    )


def _manifest_to_type_info(manifest: Any) -> ConnectorTypeInfo:
    """Convert a ConnectorManifest to the API response shape."""
    return ConnectorTypeInfo(
        name=manifest.name,
        version=manifest.version,
        description=manifest.description,
        capabilities=[c.value for c in manifest.capabilities],
        transport=manifest.transport.value,
        config_schema=[
            ConnectorConfigFieldInfo(
                name=f.name,
                description=f.description,
                required=f.required,
                secret=f.secret,
                default=f.default,
            )
            for f in manifest.config_schema
        ],
    )


def _validate_type_and_config(connector_type: str, config: dict[str, Any]) -> None:
    """Reject unknown connector_type (HTTP 422) or invalid config (HTTP 422)."""
    manifest = REGISTRY.get_manifest(connector_type)
    if manifest is None:
        known = ", ".join(REGISTRY.list_types()) or "(none)"
        raise HTTPException(
            status_code=422,
            detail=f"Unknown connector type '{connector_type}'. Known types: {known}.",
        )
    errors = validate_config(manifest, config)
    if errors:
        raise HTTPException(
            status_code=422,
            detail={"message": "Connector config validation failed.", "errors": errors},
        )


# ── Discovery ─────────────────────────────────────────────────────────────────


@router.get("/types", response_model=ConnectorTypesResponse)
def list_connector_types() -> ConnectorTypesResponse:
    """List all registered connector types with their config schemas."""
    manifests = REGISTRY.list_manifests()
    items = [_manifest_to_type_info(m) for m in manifests]
    return ConnectorTypesResponse(items=items, total=len(items))


# ── CRUD ──────────────────────────────────────────────────────────────────────


@router.get("", response_model=ConnectorListResponse)
def list_connectors() -> ConnectorListResponse:
    """List all registered connectors."""
    items = _repo.list_all()
    return ConnectorListResponse(items=[_to_response(c) for c in items], total=len(items))


@router.post("", response_model=ConnectorResponse, status_code=201)
def create_connector(body: ConnectorCreateRequest) -> ConnectorResponse:
    """Register a new connector.

    Rejects unknown ``connector_type`` values (HTTP 422) and config fields
    that do not match the manifest schema.
    """
    _validate_type_and_config(body.connector_type, body.config)
    db = _repo.create(
        connector_id=body.connector_id,
        name=body.name,
        connector_type=body.connector_type,
        config=body.config,
    )
    return _to_response(db)


@router.get("/{connector_id}", response_model=ConnectorResponse)
def get_connector(connector_id: str) -> ConnectorResponse:
    """Get connector details."""
    db = _repo.get(connector_id)
    if db is None:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")
    return _to_response(db)


@router.patch("/{connector_id}", response_model=ConnectorResponse)
def update_connector(connector_id: str, body: ConnectorUpdateRequest) -> ConnectorResponse:
    """Update connector name or configuration.

    If a new config is supplied, it is validated against the stored connector
    type's manifest.
    """
    if body.config is not None:
        existing = _repo.get(connector_id)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")
        _validate_type_and_config(existing.connector_type, body.config)

    db = _repo.update(connector_id, name=body.name, config=body.config)
    if db is None:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")
    return _to_response(db)


@router.delete("/{connector_id}", response_model=DeleteConnectorResponse)
def delete_connector(connector_id: str) -> DeleteConnectorResponse:
    """Remove a connector registration."""
    deleted = _repo.delete(connector_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")
    return DeleteConnectorResponse(connector_id=connector_id, deleted=True)


@router.post("/{connector_id}/heartbeat", response_model=ConnectorResponse)
def connector_heartbeat(connector_id: str, body: ConnectorHeartbeatRequest) -> ConnectorResponse:
    """Connector reports its runtime status and MCP URL to the control plane."""
    db = _repo.record_heartbeat(connector_id, status=body.status, mcp_url=body.mcp_url)
    if db is None:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")
    return _to_response(db)
