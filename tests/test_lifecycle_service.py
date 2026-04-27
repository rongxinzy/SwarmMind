"""Tests for lifecycle service startup and cleanup scanner behavior."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pytest

from swarmmind.services.lifecycle import run_cleanup_once, run_cleanup_scanner, startup_lifecycle


@dataclass
class FakeProposal:
    id: str
    created_at: datetime


class FakeActionProposalRepo:
    def __init__(self, stale: list[FakeProposal] | None = None, list_error: Exception | None = None):
        self._stale = stale or []
        self._list_error = list_error
        self.rejected_ids: list[str] = []
        self.list_stale_calls: list[int] = []

    def list_stale(self, timeout_seconds: int):
        self.list_stale_calls.append(timeout_seconds)
        if self._list_error is not None:
            raise self._list_error
        return self._stale

    def reject_proposal(self, proposal_id: str) -> None:
        self.rejected_ids.append(proposal_id)


class FakeMemoryRepo:
    def __init__(self, deleted: int = 0):
        self.deleted = deleted
        self.delete_calls = 0

    def delete_expired(self) -> int:
        self.delete_calls += 1
        return self.deleted


class FakeThread:
    def __init__(self, target, daemon):
        self.target = target
        self.daemon = daemon
        self.started = False

    def start(self) -> None:
        self.started = True


def test_startup_lifecycle_runs_bootstrap_and_starts_cleanup_thread() -> None:
    calls: list[str] = []
    built_threads: list[FakeThread] = []

    def fake_thread_factory(*, target, daemon):
        thread = FakeThread(target=target, daemon=daemon)
        built_threads.append(thread)
        return thread

    def fake_cleanup() -> None:
        return None

    startup_lifecycle(
        init_db=lambda: calls.append("init_db"),
        seed_default_agents=lambda: calls.append("seed_default_agents"),
        seed_builtin_agent_teams=lambda: calls.append("seed_builtin_agent_teams"),
        sync_env_runtime_model=lambda: calls.append("sync_env_runtime_model"),
        ensure_default_runtime_instance=lambda: calls.append("ensure_default_runtime_instance"),
        cleanup_scanner=fake_cleanup,
        api_host="127.0.0.1",
        api_port=8000,
        thread_factory=fake_thread_factory,
    )

    assert calls == [
        "init_db",
        "seed_default_agents",
        "seed_builtin_agent_teams",
        "sync_env_runtime_model",
        "ensure_default_runtime_instance",
    ]
    assert len(built_threads) == 1
    assert built_threads[0].target is fake_cleanup
    assert built_threads[0].daemon is True
    assert built_threads[0].started is True


def test_run_cleanup_once_matches_supervisor_cleanup_behavior() -> None:
    action_repo = FakeActionProposalRepo(
        stale=[
            FakeProposal(id="p-1", created_at=datetime(2026, 1, 1, 0, 0, 0)),
            FakeProposal(id="p-2", created_at=datetime(2026, 1, 1, 0, 1, 0)),
        ]
    )
    memory_repo = FakeMemoryRepo(deleted=3)
    decisions: list[tuple[str, str]] = []

    run_cleanup_once(
        action_proposal_repo=action_repo,
        memory_repo=memory_repo,
        action_timeout_seconds=42,
        record_supervisor_decision=lambda proposal_id, decision: decisions.append((proposal_id, decision)),
        supervisor_timeout_decision="TIMEOUT",
    )

    assert action_repo.list_stale_calls == [42]
    assert action_repo.rejected_ids == ["p-1", "p-2"]
    assert decisions == [("p-1", "TIMEOUT"), ("p-2", "TIMEOUT")]
    assert memory_repo.delete_calls == 1


def test_run_cleanup_scanner_catches_iteration_errors_without_crashing() -> None:
    action_repo = FakeActionProposalRepo(list_error=RuntimeError("boom"))
    memory_repo = FakeMemoryRepo()
    sleep_calls = {"count": 0}

    def fake_sleep(seconds: float) -> None:
        sleep_calls["count"] += 1
        if sleep_calls["count"] > 1:
            raise StopIteration("stop test loop")

    with pytest.raises(StopIteration):
        run_cleanup_scanner(
            action_proposal_repo=action_repo,
            memory_repo=memory_repo,
            action_timeout_seconds=30,
            record_supervisor_decision=lambda *_: None,
            supervisor_timeout_decision="TIMEOUT",
            sleeper=fake_sleep,
        )

    assert action_repo.list_stale_calls == [30]
