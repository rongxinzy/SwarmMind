"""Strategy table repository."""

from __future__ import annotations

from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import StrategyTableDB


class StrategyRepository:
    """Repository for routing strategy operations."""

    def get_agent_id(self, situation_tag: str) -> str | None:
        """Look up strategy_table for the given situation_tag."""
        with session_scope() as session:
            entry = session.get(StrategyTableDB, situation_tag)
            return entry.agent_id if entry else None

    def update_outcome(self, situation_tag: str, success: bool) -> None:
        """Update success/failure counts in strategy_table after a completed task."""
        with session_scope() as session:
            entry = session.get(StrategyTableDB, situation_tag)
            if entry is not None:
                if success:
                    entry.success_count += 1
                else:
                    entry.failure_count += 1

    def list_all(self) -> list[StrategyTableDB]:
        """List all strategy entries ordered by situation_tag."""
        with session_scope() as session:
            results = session.exec(
                select(StrategyTableDB).order_by(StrategyTableDB.situation_tag),
            ).all()
            for r in results:
                session.expunge(r)
            return list(results)
