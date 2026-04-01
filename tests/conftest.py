"""Test bootstrap helpers.

Provide lightweight stubs for optional runtime integrations when the local
test environment does not have the full DeerFlow + LiteLLM stack installed.
Production code still treats these as normal runtime dependencies.
"""

from __future__ import annotations

import sys
from types import ModuleType


def _ensure_litellm_stub() -> None:
    try:
        import litellm  # noqa: F401
        return
    except ModuleNotFoundError:
        pass

    litellm = ModuleType("litellm")
    litellm.drop_params = False
    litellm.modify_params = False

    def _completion(*args, **kwargs):
        raise RuntimeError("litellm stub called during tests without monkeypatch")

    async def _acompletion(*args, **kwargs):
        raise RuntimeError("litellm stub called during tests without monkeypatch")

    litellm.completion = _completion
    litellm.acompletion = _acompletion
    sys.modules["litellm"] = litellm


def _ensure_deerflow_stub() -> None:
    try:
        import deerflow.client  # noqa: F401
        return
    except ModuleNotFoundError:
        pass

    deerflow = ModuleType("deerflow")
    client = ModuleType("deerflow.client")

    class DeerFlowClient:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def stream(self, *args, **kwargs):
            return iter(())

    client.DeerFlowClient = DeerFlowClient
    deerflow.client = client
    sys.modules["deerflow"] = deerflow
    sys.modules["deerflow.client"] = client


_ensure_litellm_stub()
_ensure_deerflow_stub()
