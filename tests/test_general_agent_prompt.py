"""Tests for SwarmMind-branded runtime prompt injection."""

from __future__ import annotations

from swarmmind.db import init_db, seed_default_agents
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


def test_seed_default_agents_updates_general_identity_prompt(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    init_db()

    from swarmmind.db import get_session
    from swarmmind.db_models import AgentDB

    session = get_session()
    try:
        session.add(AgentDB(agent_id="general", domain="general", system_prompt="legacy prompt"))
        session.commit()
    finally:
        session.close()

    seed_default_agents()

    session = get_session()
    try:
        row = session.get(AgentDB, "general")
    finally:
        session.close()

    assert row is not None
    assert "SwarmMind" in row.system_prompt
    assert "北京容芯致远科技有限公司" in row.system_prompt
    assert "有什么我可以帮你的吗？" in row.system_prompt
