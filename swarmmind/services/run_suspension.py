"""In-process run suspension primitives.

Keyed by run_id. This is process-local — it does not survive restarts.
On startup, any run left in 'waiting_approval' status is failed by the
cleanup scanner in supervisor.py (see _cleanup_scanner).
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_registry: dict[str, _SuspensionSlot] = {}


@dataclass
class _SuspensionSlot:
    event: threading.Event = field(default_factory=threading.Event)
    decision: str | None = None  # 'approved' | 'rejected'
    reason: str | None = None


def register(run_id: str) -> None:
    """Register a run as suspendable. Call before starting the stream."""
    with _lock:
        _registry[run_id] = _SuspensionSlot()
    logger.debug("Suspension slot registered: run_id=%s", run_id)


def wait(run_id: str, timeout: float = 300.0) -> tuple[str | None, str | None]:
    """Block until the run is resolved or the timeout expires.

    Returns (decision, reason). Decision is None if timed out.
    """
    with _lock:
        slot = _registry.get(run_id)
    if slot is None:
        logger.warning("wait() called for unregistered run_id=%s", run_id)
        return None, None
    signalled = slot.event.wait(timeout=timeout)
    if not signalled:
        logger.warning("Suspension timed out: run_id=%s", run_id)
        return None, None
    return slot.decision, slot.reason


def resolve(run_id: str, decision: str, reason: str | None = None) -> bool:
    """Signal a decision for a suspended run.

    Returns True if the slot existed (i.e. the run was actually suspended).
    """
    with _lock:
        slot = _registry.get(run_id)
    if slot is None:
        logger.warning("resolve() called for unknown run_id=%s", run_id)
        return False
    slot.decision = decision
    slot.reason = reason
    slot.event.set()
    logger.info("Run suspension resolved: run_id=%s decision=%s", run_id, decision)
    return True


def cancel(run_id: str) -> None:
    """Cancel a suspended run (e.g. on process shutdown or timeout cleanup)."""
    resolve(run_id, "cancelled")


def deregister(run_id: str) -> None:
    """Remove the suspension slot for a completed run."""
    with _lock:
        _registry.pop(run_id, None)
    logger.debug("Suspension slot deregistered: run_id=%s", run_id)


def pending_run_ids() -> list[str]:
    """Return all run_ids that are currently suspended (event not yet set)."""
    with _lock:
        return [rid for rid, slot in _registry.items() if not slot.event.is_set()]
