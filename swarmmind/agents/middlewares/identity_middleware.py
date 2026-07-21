"""SwarmMind product identity injection for the native DeerFlow agent chain."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware, ModelRequest
from langchain_core.messages import SystemMessage

from swarmmind.prompting import rewrite_swarmmind_identity_prompt


class SwarmMindIdentityMiddleware(AgentMiddleware):
    """Rewrite DeerFlow's role block without replacing its native middleware chain."""

    def __init__(self, product_identity: str) -> None:
        super().__init__()
        self._product_identity = product_identity

    def _with_swarmmind_identity(self, request: ModelRequest) -> ModelRequest:
        system_message = request.system_message
        if system_message is not None and not isinstance(system_message.content, str):
            return request

        base_prompt = system_message.content if system_message is not None else ""
        content = rewrite_swarmmind_identity_prompt(base_prompt, self._product_identity)
        next_system_message = (
            system_message.model_copy(update={"content": content})
            if system_message is not None
            else SystemMessage(content=content)
        )
        return request.override(system_message=next_system_message)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Any],
    ) -> Any:
        """Inject product identity for synchronous model calls."""
        return handler(self._with_swarmmind_identity(request))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[Any]],
    ) -> Any:
        """Inject product identity for asynchronous model calls."""
        return await handler(self._with_swarmmind_identity(request))
