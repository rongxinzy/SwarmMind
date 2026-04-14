"""Lifecycle service for startup bootstrap and cleanup scanner responsibilities."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


def startup_lifecycle(  # noqa: PLR0913
    *,
    init_db: Callable[[], None],
    seed_default_agents: Callable[[], None],
    sync_env_runtime_model: Callable[[], None],
    ensure_default_runtime_instance: Callable[[], None],
    cleanup_scanner: Callable[[], None],
    api_host: str,
    api_port: int | str,
    thread_factory: Callable[..., Any] = threading.Thread,
    lifecycle_logger: logging.Logger = logger,
) -> Any:
    """Run startup initialization and launch cleanup scanner in background."""
    init_db()
    seed_default_agents()
    sync_env_runtime_model()
    ensure_default_runtime_instance()
    lifecycle_logger.info("SwarmMind API started on %s:%s", api_host, api_port)
    scanner_thread = thread_factory(target=cleanup_scanner, daemon=True)
    scanner_thread.start()
    return scanner_thread


def run_cleanup_once(
    *,
    action_proposal_repo: Any,
    memory_repo: Any,
    action_timeout_seconds: int,
    record_supervisor_decision: Callable[[str, Any], None],
    supervisor_timeout_decision: Any,
    lifecycle_logger: logging.Logger = logger,
) -> None:
    """Run a single cleanup pass for stale proposals and expired memory."""
    stale = action_proposal_repo.list_stale(action_timeout_seconds)
    for proposal in stale:
        lifecycle_logger.info(
            "Auto-rejecting stale proposal: id=%s (created=%s)",
            proposal.id,
            proposal.created_at,
        )
        action_proposal_repo.reject_proposal(proposal.id)
        record_supervisor_decision(proposal.id, supervisor_timeout_decision)

    deleted_memory = memory_repo.delete_expired()
    if deleted_memory > 0:
        lifecycle_logger.info("Cleaned up %d expired memory entries.", deleted_memory)


def run_cleanup_scanner(
    *,
    action_proposal_repo: Any,
    memory_repo: Any,
    action_timeout_seconds: int,
    record_supervisor_decision: Callable[[str, Any], None],
    supervisor_timeout_decision: Any,
    lifecycle_logger: logging.Logger = logger,
    sleep_seconds: int = 30,
    sleeper: Callable[[float], None] = time.sleep,
) -> None:
    """Background loop: periodically clean stale proposals and expired memory."""
    while True:
        sleeper(sleep_seconds)
        try:
            run_cleanup_once(
                action_proposal_repo=action_proposal_repo,
                memory_repo=memory_repo,
                action_timeout_seconds=action_timeout_seconds,
                record_supervisor_decision=record_supervisor_decision,
                supervisor_timeout_decision=supervisor_timeout_decision,
                lifecycle_logger=lifecycle_logger,
            )
        except Exception as exc:
            lifecycle_logger.error("Cleanup scanner error: %s", exc)
