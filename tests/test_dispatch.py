"""Tests for ContextBroker dispatch and routing logic."""

import pytest

from swarmmind.context_broker import derive_situation_tag, route_to_agent
from swarmmind.db import init_db, seed_default_agents


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    """Use a temporary DB for each test."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    init_db()
    seed_default_agents()
    yield


class TestDeriveSituationTag:
    def test_finance_keywords(self):
        assert derive_situation_tag("Generate the Q3 financial report") == "finance"
        assert derive_situation_tag("What is our quarterly revenue?") == "finance"
        assert derive_situation_tag("Analyze the expense report") == "finance"
        assert derive_situation_tag("Q4 fiscal year budget forecast") == "finance"

    def test_code_review_keywords(self):
        assert derive_situation_tag("Review this Python PR for me") == "code_review"
        assert derive_situation_tag("Check the code for bugs") == "code_review"
        assert derive_situation_tag("Refactor the API module") == "code_review"

    def test_unknown(self):
        assert derive_situation_tag("What's the weather like?") == "unknown"


class TestRouteToAgent:
    def test_finance_routes_to_general_runtime_entry(self):
        agent_id = route_to_agent("finance_qa")
        assert agent_id == "general"

    def test_code_routes_to_general_runtime_entry(self):
        agent_id = route_to_agent("code_review")
        assert agent_id == "general"

    def test_unknown_situation_falls_back_to_general(self):
        agent_id = route_to_agent("competitive_analysis")
        assert agent_id == "general"


class TestDispatch:
    def test_dispatch_finance_goal(self):
        from swarmmind.context_broker import dispatch

        result = dispatch("Generate the Q3 financial summary for Acme Corp")
        assert result.agent_id == "general"
        assert result.status == "pending"
        assert result.action_proposal_id is not None

    def test_dispatch_code_goal(self):
        from swarmmind.context_broker import dispatch

        result = dispatch("Review the new payment API PR")
        assert result.agent_id == "general"
        assert result.status == "pending"

    def test_dispatch_unknown_goal_routes_to_general_agent(self):
        from swarmmind.context_broker import dispatch

        result = dispatch("Make me a sandwich")
        assert result.agent_id == "general"
        assert result.status == "pending"


class TestDispatchMemoryContext:
    def test_dispatch_returns_memory_ctx_with_session_id(self):
        from swarmmind.context_broker import dispatch

        result = dispatch(
            "Generate the Q3 financial summary",
            user_id="alice",
            session_id="session-123",
            project_id="proj-abc",
        )

        assert result.memory_ctx is not None
        assert result.memory_ctx.user_id == "alice"
        assert result.memory_ctx.session_id == "session-123"
        assert result.memory_ctx.project_id == "proj-abc"
        assert result.memory_ctx.visible_scopes[0].layer.value == "L1_tmp"  # L1 first

    def test_dispatch_returns_memory_ctx_on_no_route(self):
        from swarmmind.context_broker import dispatch

        result = dispatch("Make me a sandwich")
        assert result.memory_ctx is not None
        assert result.memory_ctx.user_id == "default_user"

    def test_dispatch_ctx_priority_order(self):
        from swarmmind.context_broker import dispatch

        result = dispatch(
            "Review this PR",
            user_id="alice",
            team_id="team-x",
            session_id="session-abc",
        )

        scopes = result.memory_ctx.visible_scopes
        assert scopes[0].layer.value == "L1_tmp"  # session first
        assert scopes[1].layer.value == "L2_team"  # team second
        assert scopes[2].layer.value == "L4_user_soul"  # user last


class TestStrategyTableUpdate:
    def test_success_count_increments(self):
        from swarmmind.context_broker import update_strategy_on_outcome
        from swarmmind.db import get_session
        from swarmmind.db_models import StrategyTableDB

        session = get_session()
        try:
            row = session.get(StrategyTableDB, "finance_qa")
            before = row.success_count if row else 0
        finally:
            session.close()

        update_strategy_on_outcome("finance_qa", "finance", success=True)

        session = get_session()
        try:
            row = session.get(StrategyTableDB, "finance_qa")
            after = row.success_count if row else 0
        finally:
            session.close()

        assert after == before + 1

    def test_failure_count_increments(self):
        from swarmmind.context_broker import update_strategy_on_outcome
        from swarmmind.db import get_session
        from swarmmind.db_models import StrategyTableDB

        session = get_session()
        try:
            row = session.get(StrategyTableDB, "finance_qa")
            before = row.failure_count if row else 0
        finally:
            session.close()

        update_strategy_on_outcome("finance_qa", "finance", success=False)

        session = get_session()
        try:
            row = session.get(StrategyTableDB, "finance_qa")
            after = row.failure_count if row else 0
        finally:
            session.close()

        assert after == before + 1
