"""Tests for SwarmMind-branded runtime prompt injection."""

from __future__ import annotations

from langchain.agents.middleware import ModelRequest
from langchain_core.messages import SystemMessage

from swarmmind.agents.deerflow_runtime import _SwarmMindDeerFlowClientMixin
from swarmmind.agents.middlewares.identity_middleware import SwarmMindIdentityMiddleware
from swarmmind.prompting import SWARMMIND_PRODUCT_IDENTITY_PROMPT, rewrite_swarmmind_identity_prompt


def test_rewrite_swarmmind_identity_prompt_replaces_deerflow_role():
    base_prompt = """<role>
You are DeerFlow 2.0, an open-source super agent.
</role>

<thinking_style>
- Think carefully
</thinking_style>
"""
    prompt = rewrite_swarmmind_identity_prompt(base_prompt, SWARMMIND_PRODUCT_IDENTITY_PROMPT)

    assert (
        "You are SwarmMind, a next-generation AIOS product developed by Beijing Rongxin Zhiyuan Technology Co., Ltd."
        in prompt
    )
    assert "Do not present yourself as DeerFlow, Deer-Flow, or an open-source super agent." in prompt
    assert 'When the user asks who you are or greets you with questions like "你好，你是谁"' in prompt
    assert "<product_identity>" in prompt
    assert SWARMMIND_PRODUCT_IDENTITY_PROMPT in prompt
    assert "你好！我是 SwarmMind，由北京容芯致远科技有限公司开发的下一代AIOS多智能体协作平台。" in prompt
    assert "You are DeerFlow 2.0, an open-source super agent." not in prompt


def test_identity_middleware_rewrites_native_deerflow_model_request():
    middleware = SwarmMindIdentityMiddleware(SWARMMIND_PRODUCT_IDENTITY_PROMPT)
    request = ModelRequest(
        model=object(),
        messages=[],
        system_message=SystemMessage(
            content="""<role>
You are DeerFlow 2.0, an open-source super agent.
</role>

<thinking_style>Think carefully.</thinking_style>
"""
        ),
    )

    rewritten = middleware._with_swarmmind_identity(request)

    assert rewritten.system_message is not None
    assert isinstance(rewritten.system_message.content, str)
    assert "You are SwarmMind" in rewritten.system_message.content
    assert "You are DeerFlow 2.0" not in rewritten.system_message.content
    assert "<thinking_style>Think carefully.</thinking_style>" in rewritten.system_message.content


def test_client_mixin_does_not_replace_native_deerflow_runtime_methods():
    assert "_ensure_agent" not in _SwarmMindDeerFlowClientMixin.__dict__
    assert "astream" not in _SwarmMindDeerFlowClientMixin.__dict__


