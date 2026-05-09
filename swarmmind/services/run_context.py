"""RunContext value object for project-scoped execution."""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass


class RiskPolicy(str, enum.Enum):
    """Determines which capability risk tiers trigger approval gates."""

    PERMISSIVE = "permissive"  # never pauses for approval
    MODERATE = "moderate"  # pauses on high-risk capabilities only
    STRICT = "strict"  # pauses on medium or high-risk capabilities


@dataclass(frozen=True)
class RunContext:
    """Immutable context for a single execution run.

    When project_id is None this is a plain ChatSession run and all governance
    hooks (lifecycle persistence, approval gates, audit) are no-ops.
    """

    run_id: str
    project_id: str | None
    conversation_id: str
    risk_policy: RiskPolicy
    approver_role: str | None

    @classmethod
    def for_chat_session(cls, conversation_id: str) -> RunContext:
        """Create a no-project context for a plain ChatSession run."""
        return cls(
            run_id=str(uuid.uuid4()),
            project_id=None,
            conversation_id=conversation_id,
            risk_policy=RiskPolicy.PERMISSIVE,
            approver_role=None,
        )

    @classmethod
    def for_project(
        cls,
        project_id: str,
        conversation_id: str,
        *,
        risk_policy: RiskPolicy = RiskPolicy.MODERATE,
        approver_role: str | None = None,
    ) -> RunContext:
        """Create a project-scoped run context."""
        return cls(
            run_id=str(uuid.uuid4()),
            project_id=project_id,
            conversation_id=conversation_id,
            risk_policy=risk_policy,
            approver_role=approver_role,
        )
