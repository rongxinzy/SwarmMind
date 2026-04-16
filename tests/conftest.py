"""Test bootstrap helpers.

Provide lightweight stubs for optional runtime integrations when the local
test environment does not have the full DeerFlow + LiteLLM stack installed.
Production code still treats these as normal runtime dependencies.
"""

from __future__ import annotations

import os
import sys
from types import ModuleType

import pytest

from swarmmind.db import dispose_engines


def _ensure_litellm_stub() -> None:
    try:
        import litellm

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
        import deerflow.client

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

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")


@pytest.fixture(autouse=True)
def cleanup_db_engines():
    """Keep test DB engine lifecycle bounded when URLs change across cases."""
    dispose_engines()
    yield
    dispose_engines()


import asyncio


@pytest.fixture(autouse=True)
def cleanup_asyncio_loop():
    yield
    policy = asyncio.get_event_loop_policy()
    loop = getattr(policy._local, "_loop", None)
    if loop is None:
        return
    if loop.is_running():
        return
    if not loop.is_closed():
        loop.close()
    try:
        policy.set_event_loop(None)
    except NotImplementedError:
        pass
