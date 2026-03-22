"""Unified LLM client — single place for all LLM API calls.

Phase 1: uses litellm for both streaming and non-streaming calls.
Phase 2: swap this implementation for any provider's SDK.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Literal

import litellm

from swarmmind.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_PROVIDER

logger = logging.getLogger(__name__)

# Enable LiteLLM features for cross-provider compatibility:
# - drop_params=True: silently drops params the model doesn't support (no error)
# - modify_params=True: auto-translates params across provider boundaries
litellm.drop_params = True
litellm.modify_params = True


class LLMError(Exception):
    """Base exception for LLM errors."""
    pass


# ---- Reasoning configuration ----

ReasoningLevel = Literal["none", "minimum", "low", "medium", "high", "xhigh"]


@dataclass
class ReasoningConfig:
    """
    Unified reasoning/thinking config — single interface across all providers.

    Args:
        enabled: whether to enable extended reasoning (default False for speed).
        level: reasoning effort level (only meaningful when enabled=True).
               Values: none | minimum | low | medium | high | xhigh
               DashScope qwen: none=off, minimum=ultra-short, low/medium/high/xhigh = increasing depth.
               OpenAI: maps to reasoning_effort values.
               Anthropic: maps to thinking budget_tokens.
    """

    enabled: bool = False
    level: ReasoningLevel = "medium"


# ---- Per-provider reasoning parameter mapping ----
#
# Each provider uses different field names and value schemes.
# Keys are provider prefixes used in litellm model strings (e.g. "openai/", "anthropic/").
# Values are callables that translate ReasoningConfig → extra_body dict.

_PROVIDER_REASONING_HANDLERS: dict[str, callable[[ReasoningConfig], dict]] = {}


def _register_reasoning_handler(provider_prefix: str):
    """Decorator to register a reasoning handler for a provider prefix."""

    def decorator(func: callable[[ReasoningConfig], dict]):
        _PROVIDER_REASONING_HANDLERS[provider_prefix] = func
        return func

    return decorator


@_register_reasoning_handler("openai/")
def _openai_reasoning(cfg: ReasoningConfig) -> dict:
    """
    OpenAI (and OpenAI-compatible APIs like DashScope):
    - reasoning_effort=none → disable extended reasoning
    - reasoning_effort=minimum|low|medium|high|xhigh → set reasoning depth
    """
    if not cfg.enabled:
        return {"reasoning_effort": "none"}
    return {"reasoning_effort": cfg.level}


@_register_reasoning_handler("anthropic/")
def _anthropic_reasoning(cfg: ReasoningConfig) -> dict:
    """
    Anthropic Claude:
    - thinking.type="disabled" when disabled
    - thinking.type="enabled" + budget_tokens when enabled
    """
    if not cfg.enabled:
        return {"thinking": {"type": "disabled"}}
    # Map level to approximate token budget
    budget_map: dict[ReasoningLevel, int] = {
        "none": 0,
        "minimum": 256,
        "low": 512,
        "medium": 1024,
        "high": 2048,
        "xhigh": 4096,
    }
    return {"thinking": {"type": "enabled", "budget_tokens": budget_map[cfg.level]}}


def apply_reasoning_config(model: str, cfg: ReasoningConfig) -> dict:
    """
    Translate ReasoningConfig to provider-specific extra_body dict.

    Falls back to OpenAI-style (reasoning_effort) for unregistered providers,
    which covers DashScope, Ollama, and most OpenAI-compatible APIs.
    """
    for prefix, handler in _PROVIDER_REASONING_HANDLERS.items():
        if model.startswith(prefix):
            return handler(cfg)
    # Default: assume OpenAI-compatible (DashScope, Ollama, etc.)
    return _openai_reasoning(cfg)


def _clear_proxy_env() -> dict:
    """Remove proxy env vars to prevent proxy interference with LLM API calls."""
    env_backup = {}
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        if var in os.environ:
            env_backup[var] = os.environ.pop(var)
    return env_backup


class LLMClient:
    """
    Unified LLM client.

    Uses httpx to call the configured provider's API directly.
    All agents and the renderer should use this class — never call
    the API directly in other modules.
    """

    def __init__(self):
        self.provider = LLM_PROVIDER
        self.model = LLM_MODEL
        self.api_key = LLM_API_KEY
        self.base_url = LLM_BASE_URL

        if not self.api_key:
            raise LLMError(
                f"No API key configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY. "
                f"provider={self.provider}"
            )

    def complete(self, prompt: str, max_tokens: int = 4096, reasoning: bool = False) -> str:
        """
        Send a prompt and return the LLM's text response.

        Args:
            prompt: the full prompt to send
            max_tokens: max tokens in response
            reasoning: whether to enable reasoning/thinking mode (default False for speed)

        Returns:
            The LLM's text response string.

        Raises:
            LLMError: on any failure (auth, timeout, parse error)
        """
        litellm_model = f"{self.provider}/{self.model}"
        messages = [{"role": "user", "content": prompt}]
        kwargs = {
            "model": litellm_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "api_key": self.api_key,
        }
        if self.base_url:
            kwargs["api_base"] = self.base_url

        # Apply unified reasoning config (provider-specific parameter translation)
        reason_cfg = ReasoningConfig(enabled=reasoning)
        kwargs["extra_body"] = apply_reasoning_config(litellm_model, reason_cfg)

        # litellm respects this for per-request timeout
        kwargs["request_timeout"] = 120
        # Disable litellm's default retry behavior — DashScope qwen models
        # can be slow and retries compound latency. Fail fast instead.
        kwargs["max_retries"] = 0

        # Clear proxy env vars for this request to prevent proxy interference
        env_backup = _clear_proxy_env()

        try:
            response = litellm.completion(**kwargs)
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error("LLM completion error: %s", e)
            raise LLMError(f"LLM completion failed: {e}")
        finally:
            # Restore env vars
            os.environ.update(env_backup)

    async def stream(self, messages: list[dict], max_tokens: int = 1024, reasoning: bool = False):
        """
        Stream LLM response chunks as async generator.

        Yields:
            dict with optional 'content' or 'reasoning_content' text delta,
            and 'finish' when the stream ends.

        Args:
            messages: list of {"role": "user"|"assistant", "content": "..."}
            max_tokens: max tokens in response
            reasoning: whether to enable reasoning/thinking mode (default False for speed)
        """
        litellm_model = f"{self.provider}/{self.model}"
        kwargs = {
            "model": litellm_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": True,
            "api_key": self.api_key,
        }
        if self.base_url:
            kwargs["api_base"] = self.base_url

        # Apply unified reasoning config (provider-specific parameter translation)
        reason_cfg = ReasoningConfig(enabled=reasoning)
        kwargs["extra_body"] = apply_reasoning_config(litellm_model, reason_cfg)

        # Clear proxy env vars for this request to prevent proxy interference
        env_backup = _clear_proxy_env()

        try:
            stream_resp = await litellm.acompletion(**kwargs)
            async for chunk in stream_resp:
                delta = chunk["choices"][0]["delta"]
                # "content" = actual response, "reasoning_content" = thinking chain
                content_text = delta.get("content") or ""
                reasoning_text = delta.get("reasoning_content") or ""
                finish = chunk["choices"][0]["finish_reason"]
                if reasoning_text:
                    yield {"thinking": reasoning_text, "finish": finish}
                if content_text:
                    yield {"text": content_text, "finish": finish}
        except Exception as e:
            logger.error("LLM stream error: %s", e)
            yield {"error": str(e), "finish": "stop"}
        finally:
            os.environ.update(env_backup)
