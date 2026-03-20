"""Code Review Agent."""

from swarmmind.agents.base import BaseAgent


class CodeReviewAgent(BaseAgent):
    """Handles code analysis, PR reviews, and technical assessment."""

    def __init__(self):
        super().__init__(agent_id="code_review", domain="code_review")

    @property
    def domain_tags(self) -> list[str]:
        return ["code", "code_review", "bug", "refactor", "python", "test"]
