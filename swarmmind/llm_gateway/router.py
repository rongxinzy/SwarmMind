"""LLM Gateway core — routes OpenAI-compatible requests to configured providers via litellm.

Enhancements over basic routing:
- Model-level fallback configuration (per-provider)
- Provider health checking with cooldown isolation
- Gateway status exposure
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx
from litellm import Router as LiteLLMRouter
from litellm.types.router import RetryPolicy

from swarmmind.llm_gateway.models import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionUsage,
    ChatMessage,
    GatewayModelInfo,
    GatewayModelListResponse,
)
from swarmmind.repositories.llm_provider import LlmProviderRepository

logger = logging.getLogger(__name__)

HEALTH_CHECK_INTERVAL_SECONDS = 30
HEALTH_CHECK_TIMEOUT_SECONDS = 10
COOLDOWN_TIME_SECONDS = 60
ALLOWED_FAILS = 3
ROUTER_TIMEOUT_SECONDS = 120
ROUTER_NUM_RETRIES = 2
STREAM_UPSTREAM_ERROR_MESSAGE = "上游模型流式连接中断，本轮回答没有完整返回。请重试。"


@dataclass
class ProviderHealth:
    """In-memory health snapshot for a provider."""

    provider_id: str
    status: str = "unknown"  # healthy | unhealthy | unknown
    last_check_at: float = 0.0
    consecutive_failures: int = 0
    error_message: str | None = None


class LlmGateway:
    """OpenAI-compatible gateway backed by litellm Router.

    Lifecycle:
        1. Load enabled providers + models from DB
        2. Build litellm.Router with decrypted API keys + fallback + cooldown
        3. Serve /chat/completions and /models
        4. Run background health checks
        5. Refresh router when providers change
    """

    def __init__(self) -> None:
        self._router: LiteLLMRouter | None = None
        self._model_names: set[str] = set()
        self._provider_repo = LlmProviderRepository()
        self._health: dict[str, ProviderHealth] = {}
        self._health_task: asyncio.Task | None = None
        self._refresh()
        self._start_health_check()

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        """Rebuild the internal litellm Router from DB state."""
        providers = self._provider_repo.get_enabled_providers_with_models()
        if not providers:
            logger.warning("No enabled LLM providers found; Gateway will reject all requests.")
            self._router = None
            self._model_names = set()
            return

        model_list: list[dict[str, Any]] = []
        model_names: set[str] = set()
        fallbacks: list[dict[str, Any]] = []

        for provider in providers:
            api_key = self._provider_repo.get_decrypted_key(provider.provider_id)
            if not api_key:
                logger.warning(
                    "Provider %s has no decryptable API key; skipping.",
                    provider.provider_id,
                )
                continue

            for m in provider.models:
                if not m.is_enabled:
                    continue
                model_names.add(m.model_name)
                entry: dict[str, Any] = {
                    "model_name": m.model_name,
                    "litellm_params": {
                        "model": m.litellm_model,
                        "api_key": api_key,
                    },
                }
                if provider.base_url:
                    entry["litellm_params"]["api_base"] = provider.base_url
                model_list.append(entry)

                # Build fallback map for this model
                if m.fallback_model_names:
                    fallbacks.append({m.model_name: list(m.fallback_model_names)})

        if not model_list:
            logger.warning("No models available after filtering; Gateway will reject all requests.")
            self._router = None
            self._model_names = set()
            return

        # Initialize health tracking for new providers
        for provider in providers:
            if provider.provider_id not in self._health:
                self._health[provider.provider_id] = ProviderHealth(provider_id=provider.provider_id)

        try:
            retry_policy = RetryPolicy(
                RateLimitErrorRetries=3,
                TimeoutErrorRetries=2,
                InternalServerErrorRetries=2,
            )
            self._router = LiteLLMRouter(
                model_list=model_list,
                num_retries=ROUTER_NUM_RETRIES,
                timeout=ROUTER_TIMEOUT_SECONDS,
                routing_strategy="simple-shuffle",
                fallbacks=fallbacks,
                allowed_fails=ALLOWED_FAILS,
                cooldown_time=COOLDOWN_TIME_SECONDS,
                retry_policy=retry_policy,
            )
            self._model_names = model_names
            logger.info(
                "Gateway router refreshed: %d providers, %d models, %d fallback rules",
                len(providers),
                len(model_list),
                len(fallbacks),
            )
        except Exception as exc:
            logger.exception("Failed to build litellm Router: %s", exc)
            self._router = None
            self._model_names = set()

    def refresh(self) -> None:
        """Public hook to rebuild router after provider changes."""
        self._refresh()

    # ------------------------------------------------------------------
    # Health checks
    # ------------------------------------------------------------------

    def _start_health_check(self) -> None:
        """Start the background health-check loop."""
        try:
            loop = asyncio.get_running_loop()
            self._health_task = loop.create_task(self._health_check_loop())
        except RuntimeError:
            # No running loop (sync context) — health check will be lazy
            pass

    async def _health_check_loop(self) -> None:
        """Periodically ping each provider to update health status."""
        while True:
            try:
                await asyncio.sleep(HEALTH_CHECK_INTERVAL_SECONDS)
                await self._run_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("Health check loop error: %s", exc)

    async def _run_health_checks(self) -> None:
        """Ping all enabled providers and update health status."""
        providers = self._provider_repo.get_enabled_providers_with_models()
        async with httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT_SECONDS) as client:
            for provider in providers:
                if not provider.is_enabled:
                    continue
                health = self._health.get(provider.provider_id)
                if health is None:
                    health = ProviderHealth(provider_id=provider.provider_id)
                    self._health[provider.provider_id] = health

                ok, err = await self._ping_provider(client, provider)
                health.last_check_at = time.time()
                if ok:
                    health.status = "healthy"
                    health.consecutive_failures = 0
                    health.error_message = None
                else:
                    health.consecutive_failures += 1
                    health.error_message = err
                    if health.consecutive_failures >= ALLOWED_FAILS:
                        health.status = "unhealthy"
                        logger.warning(
                            "Provider %s marked unhealthy after %d consecutive failures: %s",
                            provider.provider_id,
                            health.consecutive_failures,
                            err,
                        )
                    else:
                        health.status = "degraded"

    async def _ping_provider(self, client: httpx.AsyncClient, provider: Any) -> tuple[bool, str | None]:
        """Send a lightweight probe to a provider.

        Returns (ok, error_message).
        """
        api_key = self._provider_repo.get_decrypted_key(provider.provider_id)
        if not api_key:
            return False, "No decryptable API key"

        base_url = provider.base_url or "https://api.openai.com/v1"
        if not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"

        try:
            resp = await client.get(
                f"{base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if resp.status_code == 200:
                return True, None
            return False, f"HTTP {resp.status_code}"
        except httpx.TimeoutException:
            return False, "Ping timeout"
        except Exception as exc:
            return False, str(exc)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> dict[str, Any]:
        """Return current gateway status including provider health."""
        providers = self._provider_repo.get_enabled_providers_with_models()
        provider_statuses = []
        for provider in providers:
            health = self._health.get(provider.provider_id)
            provider_statuses.append(
                {
                    "provider_id": provider.provider_id,
                    "name": provider.name,
                    "provider_type": provider.provider_type,
                    "is_enabled": provider.is_enabled,
                    "is_default": provider.is_default,
                    "health_status": health.status if health else "unknown",
                    "last_check_at": health.last_check_at if health else None,
                    "consecutive_failures": health.consecutive_failures if health else 0,
                    "error_message": health.error_message if health else None,
                    "models": [
                        {
                            "model_name": m.model_name,
                            "litellm_model": m.litellm_model,
                            "is_enabled": m.is_enabled,
                            "fallback_model_names": m.fallback_model_names,
                        }
                        for m in provider.models
                    ],
                }
            )

        return {
            "gateway_ready": self._router is not None,
            "model_count": len(self._model_names),
            "providers": provider_statuses,
            "config": {
                "allowed_fails": ALLOWED_FAILS,
                "cooldown_time_seconds": COOLDOWN_TIME_SECONDS,
                "health_check_interval_seconds": HEALTH_CHECK_INTERVAL_SECONDS,
            },
        }

    # ------------------------------------------------------------------
    # /models
    # ------------------------------------------------------------------

    def list_models(self) -> GatewayModelListResponse:
        """Return available models in OpenAI-compatible format."""
        now = int(time.time())
        data = [GatewayModelInfo(id=name, created=now) for name in sorted(self._model_names)]
        return GatewayModelListResponse(data=data)

    # ------------------------------------------------------------------
    # /chat/completions (non-streaming)
    # ------------------------------------------------------------------

    async def chat_completions(
        self,
        request: ChatCompletionRequest,
    ) -> ChatCompletionResponse:
        """Handle a non-streaming chat completion request."""
        if self._router is None:
            raise RuntimeError("Gateway router is not available. No providers configured.")

        if request.model not in self._model_names:
            raise RuntimeError(f"Model '{request.model}' is not available through the Gateway.")

        messages = [m.model_dump(exclude_none=True) for m in request.messages]
        kwargs: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
            "stream": False,
            "presence_penalty": request.presence_penalty,
            "frequency_penalty": request.frequency_penalty,
            "drop_params": True,
        }
        if request.stop is not None:
            kwargs["stop"] = request.stop
        if request.tools is not None:
            kwargs["tools"] = request.tools
        if request.tool_choice is not None:
            kwargs["tool_choice"] = request.tool_choice
        if request.response_format is not None:
            kwargs["response_format"] = request.response_format
        if request.seed is not None:
            kwargs["seed"] = request.seed
        if request.user is not None:
            kwargs["user"] = request.user

        # Remove None values
        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        response = await self._router.acompletion(**kwargs)

        # Normalize litellm response to OpenAI format
        choice = ChatCompletionChoice(
            index=0,
            message=ChatMessage(
                role=response.choices[0].message.role,
                content=response.choices[0].message.content,
            ),
            finish_reason=response.choices[0].finish_reason,
        )

        usage = None
        if hasattr(response, "usage") and response.usage:
            usage = ChatCompletionUsage(
                prompt_tokens=getattr(response.usage, "prompt_tokens", 0),
                completion_tokens=getattr(response.usage, "completion_tokens", 0),
                total_tokens=getattr(response.usage, "total_tokens", 0),
            )

        return ChatCompletionResponse(
            id=response.id if hasattr(response, "id") else f"chatcmpl-{uuid.uuid4().hex[:12]}",
            created=int(time.time()),
            model=request.model,
            choices=[choice],
            usage=usage,
        )

    # ------------------------------------------------------------------
    # /chat/completions (streaming)
    # ------------------------------------------------------------------

    async def chat_completions_stream(
        self,
        request: ChatCompletionRequest,
    ) -> AsyncIterator[str]:
        """Handle a streaming chat completion request; yields SSE lines."""
        if self._router is None:
            async for line in self._stream_error_response(
                request.model,
                "Gateway router is not available. No providers configured.",
            ):
                yield line
            return

        if request.model not in self._model_names:
            async for line in self._stream_error_response(
                request.model,
                f"Model '{request.model}' is not available through the Gateway.",
            ):
                yield line
            return

        messages = [m.model_dump(exclude_none=True) for m in request.messages]
        kwargs: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
            "stream": True,
            "presence_penalty": request.presence_penalty,
            "frequency_penalty": request.frequency_penalty,
            "drop_params": True,
        }
        if request.stop is not None:
            kwargs["stop"] = request.stop
        if request.seed is not None:
            kwargs["seed"] = request.seed

        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
        created_ts = int(time.time())

        try:
            response = await self._router.acompletion(**kwargs)
        except Exception as exc:
            logger.warning("Gateway upstream stream setup failed: %s", exc, exc_info=True)
            async for line in self._stream_error_response(
                request.model,
                self._format_stream_error_message(exc),
                completion_id=completion_id,
                created_ts=created_ts,
            ):
                yield line
            return

        yield self._sse_chunk(
            completion_id=completion_id,
            created_ts=created_ts,
            model=request.model,
            delta=ChatMessage(role="assistant"),
        )

        try:
            async for chunk in response:
                delta_content = ""
                if hasattr(chunk, "choices") and chunk.choices:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, "content") and delta.content:
                        delta_content = delta.content

                if delta_content:
                    yield self._sse_chunk(
                        completion_id=completion_id,
                        created_ts=created_ts,
                        model=request.model,
                        delta=ChatMessage(role="assistant", content=delta_content),
                    )
        except Exception as exc:
            logger.warning("Gateway upstream stream interrupted: %s", exc, exc_info=True)
            yield self._sse_chunk(
                completion_id=completion_id,
                created_ts=created_ts,
                model=request.model,
                delta=ChatMessage(role="assistant", content=self._format_stream_error_message(exc)),
            )

        yield self._sse_chunk(
            completion_id=completion_id,
            created_ts=created_ts,
            model=request.model,
            delta=ChatMessage(role="assistant"),
            finish_reason="stop",
        )
        yield "data: [DONE]\n\n"

    def _sse_chunk(
        self,
        *,
        completion_id: str,
        created_ts: int,
        model: str,
        delta: ChatMessage | None,
        finish_reason: str | None = None,
    ) -> str:
        chunk = ChatCompletionResponse(
            id=completion_id,
            object="chat.completion.chunk",
            created=created_ts,
            model=model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    delta=delta,
                    finish_reason=finish_reason,
                ),
            ],
        )
        return f"data: {chunk.model_dump_json(exclude_none=True)}\n\n"

    def _format_stream_error_message(self, exc: Exception) -> str:
        detail = str(exc)
        if "does not support parameters" in detail:
            return "本地 LLM Gateway 参数适配失败，已阻止不完整流式响应。请重试。"
        return STREAM_UPSTREAM_ERROR_MESSAGE

    async def _stream_error_response(
        self,
        model: str,
        message: str,
        *,
        completion_id: str | None = None,
        created_ts: int | None = None,
    ) -> AsyncIterator[str]:
        completion_id = completion_id or f"chatcmpl-{uuid.uuid4().hex[:12]}"
        created_ts = created_ts or int(time.time())
        yield self._sse_chunk(
            completion_id=completion_id,
            created_ts=created_ts,
            model=model,
            delta=ChatMessage(role="assistant"),
        )
        yield self._sse_chunk(
            completion_id=completion_id,
            created_ts=created_ts,
            model=model,
            delta=ChatMessage(role="assistant", content=message),
        )
        yield self._sse_chunk(
            completion_id=completion_id,
            created_ts=created_ts,
            model=model,
            delta=ChatMessage(role="assistant"),
            finish_reason="stop",
        )
        yield "data: [DONE]\n\n"


# Lazy singleton gateway instance
_gateway_instance: LlmGateway | None = None


def get_gateway() -> LlmGateway:
    """Return the singleton gateway instance, creating it on first access."""
    global _gateway_instance  # noqa: PLW0603
    if _gateway_instance is None:
        _gateway_instance = LlmGateway()
    return _gateway_instance
