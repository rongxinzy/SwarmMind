"""Task emission from DeerFlow runtime plan events.

Writes TaskDB rows when plan steps are emitted by the runtime.
All writes are idempotent on (run_id, step_key).
Silently skips emission when project_id is None (ChatSession-only runs).
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# Status map for step status updates
_STATUS_MAP = {
    "task_started": "in_progress",
    "task_running": "in_progress",
    "task_completed": "done",
    "task_failed": "blocked",
}


def _derive_step_key(step_index: int, title: str) -> str:
    """Derive a stable step_key from index + title when none is provided."""
    raw = f"{step_index}:{title.lower().strip()}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]  # noqa: S324 - not crypto


def emit_from_plan_steps(
    run_id: str | None,
    project_id: str | None,
    steps: list[dict[str, Any]],
    task_repo: Any,
) -> None:
    """Emit TaskDB rows from a plan_steps event."""
    if run_id is None or project_id is None:
        return

    for idx, step in enumerate(steps):
        title = step.get("title") or step.get("description") or f"Step {idx + 1}"
        step_key = step.get("step_key") or step.get("id") or _derive_step_key(idx, title)
        description = step.get("description")
        try:
            task_repo.upsert_step(
                run_id=run_id,
                project_id=project_id,
                step_key=str(step_key),
                title=title,
                description=description,
                status="todo",
                source_event_at=datetime.now(tz=UTC),
            )
        except Exception:
            logger.exception(
                "task_emitter: failed to upsert step run_id=%s step_key=%s",
                run_id,
                step_key,
            )


def update_step_status(
    run_id: str | None,
    project_id: str | None,
    event_type: str,
    task_id: str | None,
    task_repo: Any,
) -> None:
    """Update TaskDB status for a task_started/task_completed/task_failed event."""
    if run_id is None or project_id is None or task_id is None:
        return

    status = _STATUS_MAP.get(event_type)
    if status is None:
        return

    try:
        task_repo.update_status_by_step(run_id=run_id, step_key=task_id, status=status)
    except Exception:
        logger.exception(
            "task_emitter: failed to update step status run_id=%s step_key=%s",
            run_id,
            task_id,
        )
