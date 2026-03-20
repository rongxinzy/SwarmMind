"""Finance Q&A Agent."""

from swarmmind.agents.base import BaseAgent


class FinanceAgent(BaseAgent):
    """Handles financial analysis, Q&A, and reporting."""

    def __init__(self):
        super().__init__(agent_id="finance", domain="finance")

    @property
    def domain_tags(self) -> list[str]:
        return ["finance", "revenue", "expense", "quarterly", "fiscal", "budget"]
