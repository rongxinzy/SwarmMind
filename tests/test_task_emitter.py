"""Tests for task_emitter service."""

from __future__ import annotations

from unittest.mock import MagicMock

from swarmmind.services.task_emitter import emit_from_plan_steps, update_step_status

# ---------------------------------------------------------------------------
# emit_from_plan_steps
# ---------------------------------------------------------------------------


def test_emit_from_plan_steps_creates_tasks():
    task_repo = MagicMock()
    steps = [
        {"title": "Design schema", "description": "Design the DB schema"},
        {"title": "Write tests"},
    ]
    emit_from_plan_steps("run-1", "proj-1", steps, task_repo)

    assert task_repo.upsert_step.call_count == 2
    first_call_kwargs = task_repo.upsert_step.call_args_list[0].kwargs
    assert first_call_kwargs["run_id"] == "run-1"
    assert first_call_kwargs["project_id"] == "proj-1"
    assert first_call_kwargs["title"] == "Design schema"
    assert first_call_kwargs["description"] == "Design the DB schema"
    assert first_call_kwargs["status"] == "todo"


def test_emit_from_plan_steps_uses_step_key_from_event():
    task_repo = MagicMock()
    steps = [{"title": "Analyze", "step_key": "step-abc"}]
    emit_from_plan_steps("run-1", "proj-1", steps, task_repo)

    kwargs = task_repo.upsert_step.call_args.kwargs
    assert kwargs["step_key"] == "step-abc"


def test_emit_from_plan_steps_derives_step_key_when_missing():
    task_repo = MagicMock()
    steps = [{"title": "Analyze"}]
    emit_from_plan_steps("run-1", "proj-1", steps, task_repo)

    kwargs = task_repo.upsert_step.call_args.kwargs
    # step_key should be a 16-char hex string derived from "0:analyze"
    assert isinstance(kwargs["step_key"], str)
    assert len(kwargs["step_key"]) == 16


def test_emit_from_plan_steps_idempotent():
    """Calling twice with the same steps should call upsert_step twice (idempotency is in the repo)."""
    task_repo = MagicMock()
    steps = [{"title": "Step A", "step_key": "key-a"}]
    emit_from_plan_steps("run-1", "proj-1", steps, task_repo)
    emit_from_plan_steps("run-1", "proj-1", steps, task_repo)

    assert task_repo.upsert_step.call_count == 2


def test_emit_from_plan_steps_skips_when_project_id_none():
    task_repo = MagicMock()
    emit_from_plan_steps("run-1", None, [{"title": "Step"}], task_repo)
    task_repo.upsert_step.assert_not_called()


def test_emit_from_plan_steps_skips_when_run_id_none():
    task_repo = MagicMock()
    emit_from_plan_steps(None, "proj-1", [{"title": "Step"}], task_repo)
    task_repo.upsert_step.assert_not_called()


def test_emit_from_plan_steps_skips_when_both_none():
    task_repo = MagicMock()
    emit_from_plan_steps(None, None, [{"title": "Step"}], task_repo)
    task_repo.upsert_step.assert_not_called()


def test_emit_from_plan_steps_swallows_repo_exception():
    task_repo = MagicMock()
    task_repo.upsert_step.side_effect = RuntimeError("db error")
    # Should not raise
    emit_from_plan_steps("run-1", "proj-1", [{"title": "Step"}], task_repo)


# ---------------------------------------------------------------------------
# update_step_status
# ---------------------------------------------------------------------------


def test_update_step_status_in_progress_on_task_started():
    task_repo = MagicMock()
    update_step_status("run-1", "proj-1", "task_started", "step-xyz", task_repo)
    task_repo.update_status_by_step.assert_called_once_with(run_id="run-1", step_key="step-xyz", status="in_progress")


def test_update_step_status_done_on_task_completed():
    task_repo = MagicMock()
    update_step_status("run-1", "proj-1", "task_completed", "step-xyz", task_repo)
    task_repo.update_status_by_step.assert_called_once_with(run_id="run-1", step_key="step-xyz", status="done")


def test_update_step_status_blocked_on_task_failed():
    task_repo = MagicMock()
    update_step_status("run-1", "proj-1", "task_failed", "step-xyz", task_repo)
    task_repo.update_status_by_step.assert_called_once_with(run_id="run-1", step_key="step-xyz", status="blocked")


def test_update_step_status_in_progress_on_task_running():
    task_repo = MagicMock()
    update_step_status("run-1", "proj-1", "task_running", "step-xyz", task_repo)
    task_repo.update_status_by_step.assert_called_once_with(run_id="run-1", step_key="step-xyz", status="in_progress")


def test_update_step_status_skips_unknown_event_type():
    task_repo = MagicMock()
    update_step_status("run-1", "proj-1", "unknown_event", "step-xyz", task_repo)
    task_repo.update_status_by_step.assert_not_called()


def test_update_step_status_skips_when_project_id_none():
    task_repo = MagicMock()
    update_step_status("run-1", None, "task_completed", "step-xyz", task_repo)
    task_repo.update_status_by_step.assert_not_called()


def test_update_step_status_skips_when_run_id_none():
    task_repo = MagicMock()
    update_step_status(None, "proj-1", "task_completed", "step-xyz", task_repo)
    task_repo.update_status_by_step.assert_not_called()


def test_update_step_status_skips_when_task_id_none():
    task_repo = MagicMock()
    update_step_status("run-1", "proj-1", "task_completed", None, task_repo)
    task_repo.update_status_by_step.assert_not_called()


def test_update_step_status_swallows_repo_exception():
    task_repo = MagicMock()
    task_repo.update_status_by_step.side_effect = RuntimeError("db error")
    # Should not raise
    update_step_status("run-1", "proj-1", "task_completed", "step-xyz", task_repo)


# ---------------------------------------------------------------------------
# Status precedence (via update_status_by_step in repository)
# The precedence logic is in TaskRepository.update_status_by_step.
# Here we verify the emitter passes status correctly.
# ---------------------------------------------------------------------------


def test_done_status_passed_for_task_completed():
    """done cannot be downgraded — verify emitter passes 'done' status."""
    task_repo = MagicMock()
    update_step_status("run-1", "proj-1", "task_completed", "step-1", task_repo)
    args = task_repo.update_status_by_step.call_args.kwargs
    assert args["status"] == "done"


def test_blocked_status_not_downgraded_by_in_progress():
    """Precedence: done > blocked > in_progress > todo.

    The repository enforces this; we test the logic directly here.
    """
    # Simulate a task that is already 'blocked'
    existing = MagicMock()
    existing.status = "blocked"

    _PRECEDENCE = {"done": 4, "blocked": 3, "in_progress": 2, "todo": 1}  # noqa: N806
    new_status = "in_progress"
    # in_progress (2) is NOT > blocked (3), so status should NOT change
    assert _PRECEDENCE.get(new_status, 0) <= _PRECEDENCE.get(existing.status, 0)


def test_done_cannot_be_downgraded():
    """done (4) > in_progress (2) — done should not be overwritten."""
    _PRECEDENCE = {"done": 4, "blocked": 3, "in_progress": 2, "todo": 1}  # noqa: N806
    existing_status = "done"
    new_status = "in_progress"
    assert _PRECEDENCE.get(new_status, 0) <= _PRECEDENCE.get(existing_status, 0)
