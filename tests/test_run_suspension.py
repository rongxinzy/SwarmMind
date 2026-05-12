"""Tests for swarmmind.services.run_suspension."""

import threading
import time

import pytest

from swarmmind.services import run_suspension


@pytest.fixture(autouse=True)
def _clean_registry():
    """Ensure suspension registry is empty before and after each test."""
    # Clear any leftover slots
    with run_suspension._lock:
        run_suspension._registry.clear()
    yield
    with run_suspension._lock:
        run_suspension._registry.clear()


class TestRegisterAndResolve:
    def test_resolve_signals_event(self):
        run_suspension.register("run-1")
        result = run_suspension.resolve("run-1", "approved", "looks good")
        assert result is True
        decision, reason = run_suspension.wait("run-1", timeout=0.1)
        assert decision == "approved"
        assert reason == "looks good"

    def test_resolve_unknown_returns_false(self):
        result = run_suspension.resolve("nonexistent", "approved")
        assert result is False

    def test_wait_before_resolve(self):
        run_suspension.register("run-2")

        def _resolver():
            time.sleep(0.05)
            run_suspension.resolve("run-2", "rejected", "too risky")

        t = threading.Thread(target=_resolver, daemon=True)
        t.start()

        decision, reason = run_suspension.wait("run-2", timeout=2.0)
        t.join(timeout=1.0)

        assert decision == "rejected"
        assert reason == "too risky"

    def test_wait_timeout(self):
        run_suspension.register("run-3")
        decision, reason = run_suspension.wait("run-3", timeout=0.05)
        assert decision is None
        assert reason is None

    def test_cancel(self):
        run_suspension.register("run-4")
        run_suspension.cancel("run-4")
        decision, _ = run_suspension.wait("run-4", timeout=0.1)
        assert decision == "cancelled"

    def test_deregister_removes_slot(self):
        run_suspension.register("run-5")
        run_suspension.deregister("run-5")
        with run_suspension._lock:
            assert "run-5" not in run_suspension._registry

    def test_pending_run_ids(self):
        run_suspension.register("run-a")
        run_suspension.register("run-b")
        run_suspension.resolve("run-b", "approved")

        pending = run_suspension.pending_run_ids()
        assert "run-a" in pending
        assert "run-b" not in pending

    def test_wait_unregistered_run(self):
        decision, reason = run_suspension.wait("not-registered", timeout=0.05)
        assert decision is None
        assert reason is None
