"""RunLifecycleService: persists run lifecycle transitions for project-scoped executions."""

from __future__ import annotations

import logging

from swarmmind.db_models import RunDB
from swarmmind.repositories.run import RunRepository
from swarmmind.services.run_context import RunContext

logger = logging.getLogger(__name__)


class RunLifecycleService:
    """Persists run lifecycle events for project-scoped executions.

    When ctx.project_id is None (ChatSession-only), all methods are no-ops so
    existing ChatSession flows are unaffected.
    """

    def __init__(self, run_repo: RunRepository) -> None:
        self._run_repo = run_repo

    def start(self, ctx: RunContext) -> RunDB | None:
        """Create a RunDB row for this execution. No-op for ChatSession runs."""
        if ctx.project_id is None:
            return None
        run = self._run_repo.create(
            run_id=ctx.run_id,
            project_id=ctx.project_id,
            conversation_id=ctx.conversation_id,
            status="running",
        )
        logger.info("Run started: run_id=%s project_id=%s", ctx.run_id, ctx.project_id)
        return run

    def finish(self, ctx: RunContext, summary: str | None = None) -> None:
        """Mark run as completed. No-op for ChatSession runs."""
        if ctx.project_id is None:
            return
        self._run_repo.mark_completed(ctx.run_id, summary)
        logger.info("Run finished: run_id=%s", ctx.run_id)

    def fail(self, ctx: RunContext, error_class: str, message: str) -> None:
        """Mark run as failed. No-op for ChatSession runs."""
        if ctx.project_id is None:
            return
        self._run_repo.mark_failed(ctx.run_id, error_class, message)
        logger.warning("Run failed: run_id=%s error=%s: %s", ctx.run_id, error_class, message)

    def pause_for_approval(self, ctx: RunContext, approval_id: str) -> None:
        """Mark run as waiting for approval. No-op for ChatSession runs."""
        if ctx.project_id is None:
            return
        self._run_repo.mark_waiting_approval(ctx.run_id, approval_id)
        logger.info("Run paused for approval: run_id=%s approval_id=%s", ctx.run_id, approval_id)

    def resume(self, ctx: RunContext) -> None:
        """Mark run as running again after approval. No-op for ChatSession runs."""
        if ctx.project_id is None:
            return
        self._run_repo.mark_running(ctx.run_id)
        logger.info("Run resumed: run_id=%s", ctx.run_id)
