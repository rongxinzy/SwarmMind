"""Unified LLM client — single place for all LLM API calls.

Phase 1: uses httpx directly for DashScope Anthropic-compatible endpoint.
Phase 2: swap this implementation for any provider's SDK.
"""

import json
import logging

import httpx

from swarmmind.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_PROVIDER

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM errors."""
    pass


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

    def complete(self, prompt: str, max_tokens: int = 4096) -> str:
        """
        Send a prompt and return the LLM's text response.

        Args:
            prompt: the full prompt to send
            max_tokens: max tokens in response

        Returns:
            The LLM's text response string.

        Raises:
            LLMError: on any failure (auth, timeout, parse error)
        """
        if self.provider == "anthropic":
            return self._complete_anthropic(prompt, max_tokens)
        else:
            return self._complete_openai(prompt, max_tokens)

    def _complete_anthropic(self, prompt: str, max_tokens: int) -> str:
        """Call Anthropic-compatible API (e.g. DashScope)."""
        base = (self.base_url or "https://api.anthropic.com").rstrip("/")
        url = f"{base}/messages"

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["content"][0]["text"]
        except httpx.TimeoutException:
            raise LLMError(f"LLM request timed out after 60s (provider={self.provider})")
        except httpx.HTTPStatusError as e:
            raise LLMError(f"LLM HTTP error {e.response.status_code}: {e.response.text[:200]}")
        except (KeyError, IndexError, ValueError) as e:
            raise LLMError(f"LLM response parse error: {e}")

    def _complete_openai(self, prompt: str, max_tokens: int) -> str:
        """Call OpenAI-compatible API."""
        base = (self.base_url or "https://api.openai.com/v1").rstrip("/")
        url = f"{base}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except httpx.TimeoutException:
            raise LLMError(f"LLM request timed out after 60s (provider={self.provider})")
        except httpx.HTTPStatusError as e:
            raise LLMError(f"LLM HTTP error {e.response.status_code}: {e.response.text[:200]}")
        except (KeyError, IndexError, ValueError) as e:
            raise LLMError(f"LLM response parse error: {e}")

    async def stream(self, messages: list[dict], max_tokens: int = 1024):
        """
        Stream LLM response chunks as async generator.

        Yields:
            dict with optional 'content' or 'reasoning_content' text delta,
            and 'finish' when the stream ends.

        Args:
            messages: list of {"role": "user"|"assistant", "content": "..."}
            max_tokens: max tokens in response
        """
        import litellm

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
