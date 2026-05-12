"""AuditWriter — single write path for all AuditLogDB entries.

All governance writes go through this service so the call sites remain thin.
"""

from __future__ import annotations

import logging
from typing import Any

from swarmmind.db_models import AuditLogDB

logger = logging.getLogger(__name__)


class AuditWriter:
    """Thin facade over AuditLogRepository that standardises audit event creation."""

    def __init__(self, audit_log_repo: Any) -> None:
        self._repo = audit_log_repo

    def write(  # noqa: PLR0913
        self,
        *,
        event_type: str,
        project_id: str,
        run_id: str | None = None,
        approval_id: str | None = None,
        actor: str = "system",
        actor_type: str = "system",
        decision: str | None = None,
        reason: str | None = None,
        evidence: dict | None = None,
    ) -> AuditLogDB | None:
        """Write a single audit entry. Returns the created row, or None on error."""
        try:
            entry = self._repo.create(
                audit_type=event_type,
                project_id=project_id,
                run_id=run_id,
                approval_id=approval_id,
                actor_id=actor,
                actor_type=actor_type,
                decision=decision,
                reason=reason,
                extra_data=evidence,
            )
            logger.debug(
                "Audit written: type=%s project_id=%s run_id=%s",
                event_type,
                project_id,
                run_id,
            )
            return entry
        except Exception:
            # Audit failures must never break the main flow.
            logger.exception(
                "AuditWriter.write failed: type=%s project_id=%s run_id=%s",
                event_type,
                project_id,
                run_id,
            )
            return None
