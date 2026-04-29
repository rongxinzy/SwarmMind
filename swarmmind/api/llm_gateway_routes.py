"""OpenAI-compatible LLM Gateway routes."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

from swarmmind.llm_gateway.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    GatewayModelListResponse,
)
from swarmmind.llm_gateway.router import get_gateway
from swarmmind.models import GatewayStatusResponse

router = APIRouter(tags=["gateway"])


def _verify_gateway_key(authorization: str | None) -> None:
    """Verify the Gateway authorization header."""
    from swarmmind.services.gateway_key import get_gateway_key

    expected = f"Bearer {get_gateway_key()}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid gateway key")


@router.get("/gateway/v1/models", response_model=GatewayModelListResponse)
async def list_models(
    authorization: str | None = Header(None, alias="Authorization"),
) -> GatewayModelListResponse:
    """List available models (OpenAI-compatible)."""
    _verify_gateway_key(authorization)
    return get_gateway().list_models()


@router.post("/gateway/v1/chat/completions", response_model=None)
async def chat_completions(
    request: ChatCompletionRequest,
    authorization: str | None = Header(None, alias="Authorization"),
) -> ChatCompletionResponse | StreamingResponse:
    """Chat completions (OpenAI-compatible, supports streaming)."""
    _verify_gateway_key(authorization)

    try:
        if request.stream:
            return StreamingResponse(
                get_gateway().chat_completions_stream(request),
                media_type="text/event-stream",
            )
        return await get_gateway().chat_completions(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gateway error: {exc}") from exc


@router.get("/gateway/status", response_model=GatewayStatusResponse)
def gateway_status(
    authorization: str | None = Header(None, alias="Authorization"),
) -> GatewayStatusResponse:
    """Return gateway health status and provider information."""
    _verify_gateway_key(authorization)
    return GatewayStatusResponse(**get_gateway().get_status())
