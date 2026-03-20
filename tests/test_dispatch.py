"""Tests for ContextBroker dispatch and routing logic."""

import pytest

from swarmmind.context_broker import derive_situation_tag, route_to_agent
from swarmmind.db import init_db, seed_default_agents, get_connection


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    """Use a temporary DB for each test."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("SWARMMIND_DB_PATH", db_path)
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
    def test_finance_routes_to_finance_agent(self):
        agent_id = route_to_agent("finance_qa")
        assert agent_id == "finance"

    def test_code_routes_to_code_review_agent(self):
        agent_id = route_to_agent("code_review")
        assert agent_id == "code_review"

    def test_unknown_situation_returns_none(self):
        agent_id = route_to_agent("competitive_analysis")
        assert agent_id is None


class TestDispatch:
    def test_dispatch_finance_goal(self):
        from swarmmind.context_broker import dispatch

        result = dispatch("Generate the Q3 financial summary for Acme Corp")
        assert result.agent_id == "finance"
        assert result.status == "pending"
        assert result.action_proposal_id is not None

    def test_dispatch_code_goal(self):
        from swarmmind.context_broker import dispatch

        result = dispatch("Review the new payment API PR")
        assert result.agent_id == "code_review"
        assert result.status == "pending"

    def test_dispatch_unknown_goal_returns_error_proposal(self):
        from swarmmind.context_broker import dispatch

        result = dispatch("Make me a sandwich")
        assert result.agent_id == "unknown"
        assert result.status == "no_route"


class TestStrategyTableUpdate:
    def test_success_count_increments(self):
        from swarmmind.context_broker import update_strategy_on_outcome

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT success_count FROM strategy_table WHERE situation_tag = ?",
            ("finance_qa",),
        )
        before = cursor.fetchone()["success_count"]
        conn.close()

        update_strategy_on_outcome("finance_qa", "finance", success=True)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT success_count FROM strategy_table WHERE situation_tag = ?",
            ("finance_qa",),
        )
        after = cursor.fetchone()["success_count"]
        conn.close()

        assert after == before + 1

    def test_failure_count_increments(self):
        from swarmmind.context_broker import update_strategy_on_outcome

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT failure_count FROM strategy_table WHERE situation_tag = ?",
            ("finance_qa",),
        )
        before = cursor.fetchone()["failure_count"]
        conn.close()

        update_strategy_on_outcome("finance_qa", "finance", success=False)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT failure_count FROM strategy_table WHERE situation_tag = ?",
            ("finance_qa",),
        )
        after = cursor.fetchone()["failure_count"]
        conn.close()

        assert after == before + 1
