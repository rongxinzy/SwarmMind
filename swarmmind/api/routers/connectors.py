"""REST API endpoints for connector management."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from swarmmind.models import (
    ConnectorCreateRequest,
    ConnectorHeartbeatRequest,
    ConnectorListResponse,
    ConnectorResponse,
    ConnectorUpdateRequest,
    DeleteConnectorResponse,
)
from swarmmind.repositories.connector import ConnectorRepository

router = APIRouter(prefix="/connectors", tags=["connectors"])

_repo = ConnectorRepository()


def _to_response(db) -> ConnectorResponse:  # type: ignore[no-untyped-def]
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


@router.get("", response_model=ConnectorListResponse)
def list_connectors() -> ConnectorListResponse:
    """List all registered connectors."""
    items = _repo.list_all()
    return ConnectorListResponse(items=[_to_response(c) for c in items], total=len(items))


@router.post("", response_model=ConnectorResponse, status_code=201)
def create_connector(body: ConnectorCreateRequest) -> ConnectorResponse:
    """Register a new connector."""
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
    """Update connector name or configuration."""
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
