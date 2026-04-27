"""LLM Provider management routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from swarmmind.llm_gateway.router import get_gateway
from swarmmind.models import (
    GatewayKeyResponse,
    LlmProviderCreateRequest,
    LlmProviderDetail,
    LlmProviderListResponse,
    LlmProviderUpdateRequest,
)
from swarmmind.repositories.llm_provider import LlmProviderRepository
from swarmmind.services.gateway_key import get_gateway_base_url, get_gateway_key

router = APIRouter(tags=["llm-providers"])
repo = LlmProviderRepository()


@router.get("/llm-providers", response_model=LlmProviderListResponse)
def list_providers() -> LlmProviderListResponse:
    """List all enabled LLM providers."""
    items = repo.list_all(include_disabled=False)
    return LlmProviderListResponse(items=items, total=len(items))


@router.post("/llm-providers", response_model=LlmProviderDetail, status_code=201)
def create_provider(request: LlmProviderCreateRequest) -> LlmProviderDetail:
    """Create a new LLM provider."""
    provider = repo.create(
        name=request.name,
        provider_type=request.provider_type.value,
        api_key=request.api_key,
        base_url=request.base_url,
        is_default=request.is_default,
        models=request.models,
    )
    get_gateway().refresh()
    return provider


@router.get("/llm-providers/{provider_id}", response_model=LlmProviderDetail, responses={404: {"description": "Provider not found"}})
def get_provider(provider_id: str) -> LlmProviderDetail:
    """Get a provider by ID."""
    provider = repo.get_by_id(provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.patch("/llm-providers/{provider_id}", response_model=LlmProviderDetail, responses={404: {"description": "Provider not found"}})
def update_provider(
    provider_id: str,
    request: LlmProviderUpdateRequest,
) -> LlmProviderDetail:
    """Update a provider."""
    provider = repo.update(
        provider_id=provider_id,
        name=request.name,
        api_key=request.api_key,
        base_url=request.base_url,
        is_enabled=request.is_enabled,
        is_default=request.is_default,
        models=request.models,
    )
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    get_gateway().refresh()
    return provider


@router.delete("/llm-providers/{provider_id}", status_code=204, responses={404: {"description": "Provider not found"}})
def delete_provider(provider_id: str) -> None:
    """Disable a provider."""
    ok = repo.delete(provider_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Provider not found")
    get_gateway().refresh()


@router.get("/gateway/key", response_model=GatewayKeyResponse)
def get_gateway_key_endpoint() -> GatewayKeyResponse:
    """Return the gateway key and base URL for DeerFlow configuration."""
    return GatewayKeyResponse(
        gateway_key=get_gateway_key(),
        gateway_base_url=get_gateway_base_url(),
    )
