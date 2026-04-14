"""Tests for ActionProposalRepository behavior."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi import HTTPException

from swarmmind.db import init_db, seed_default_agents, session_scope
from swarmmind.db_models import ActionProposalDB
from swarmmind.models import ProposalStatus
from swarmmind.repositories.action_proposal import ActionProposalRepository
from swarmmind.time_utils import utc_now


@pytest.fixture
def action_repo(tmp_path, monkeypatch) -> ActionProposalRepository:
    db_path = tmp_path / "action-proposals.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    init_db()
    seed_default_agents()
    return ActionProposalRepository()


def test_create_and_get_roundtrip_serializes_conditions(action_repo: ActionProposalRepository) -> None:
    proposal = action_repo.create(
        agent_id="general",
        description="analyze q3 report",
        target_resource="report.md",
        preconditions={"source": "uploaded_csv"},
        postconditions={"artifact": "summary.md"},
        confidence=0.9,
    )

    loaded = action_repo.get(proposal.id)

    assert loaded is not None
    assert loaded.description == "analyze q3 report"
    assert loaded.target_resource == "report.md"
    assert loaded.preconditions == {"source": "uploaded_csv"}
    assert loaded.postconditions == {"artifact": "summary.md"}
    assert loaded.confidence == 0.9
    assert loaded.status == ProposalStatus.PENDING


def test_update_result_persists_description_target_and_confidence(action_repo: ActionProposalRepository) -> None:
    proposal = action_repo.create(agent_id="general", description="draft")

    action_repo.update_result(
        proposal.id,
        description="final summary",
        target_resource="output.md",
        confidence=0.75,
    )

    loaded = action_repo.get(proposal.id)
    assert loaded is not None
    assert loaded.description == "final summary"
    assert loaded.target_resource == "output.md"
    assert loaded.confidence == 0.75
    assert loaded.status == ProposalStatus.PENDING


def test_approve_and_reject_proposal_enforce_pending_state(action_repo: ActionProposalRepository) -> None:
    approved = action_repo.create(agent_id="general", description="approve me")
    rejected = action_repo.create(agent_id="general", description="reject me")

    action_repo.approve(approved.id)
    action_repo.reject_proposal(rejected.id)

    assert action_repo.get(approved.id).status == ProposalStatus.APPROVED
    assert action_repo.get(rejected.id).status == ProposalStatus.REJECTED

    with pytest.raises(HTTPException) as approved_exc:
        action_repo.approve(approved.id)
    assert approved_exc.value.status_code == 409

    with pytest.raises(HTTPException) as rejected_exc:
        action_repo.reject_proposal(rejected.id)
    assert rejected_exc.value.status_code == 409


def test_approve_missing_proposal_raises_404(action_repo: ActionProposalRepository) -> None:
    with pytest.raises(HTTPException) as exc:
        action_repo.approve("missing")

    assert exc.value.status_code == 404


def test_list_pending_and_list_stale_filter_by_status_and_age(action_repo: ActionProposalRepository) -> None:
    oldest = action_repo.create(agent_id="general", description="oldest")
    middle = action_repo.create(agent_id="general", description="middle")
    newest = action_repo.create(agent_id="general", description="newest")
    approved = action_repo.create(agent_id="general", description="approved")
    action_repo.approve(approved.id)

    stale_time = utc_now() - timedelta(seconds=120)
    less_stale_time = utc_now() - timedelta(seconds=61)

    with session_scope() as session:
        oldest_db = session.get(ActionProposalDB, oldest.id)
        middle_db = session.get(ActionProposalDB, middle.id)
        newest_db = session.get(ActionProposalDB, newest.id)
        assert oldest_db and middle_db and newest_db
        oldest_db.created_at = stale_time
        middle_db.created_at = less_stale_time
        newest_db.created_at = utc_now()

    page, total = action_repo.list_pending(limit=2, offset=0)

    assert total == 3
    assert [item.id for item in page] == [oldest.id, middle.id]

    stale = action_repo.list_stale(timeout_seconds=60)
    assert [item.id for item in stale] == [oldest.id, middle.id]


def test_reject_sets_description(action_repo: ActionProposalRepository) -> None:
    proposal = action_repo.create(agent_id="general", description="initial")

    action_repo.reject(proposal.id, "runtime failed")

    loaded = action_repo.get(proposal.id)
    assert loaded is not None
    assert loaded.status == ProposalStatus.REJECTED
    assert loaded.description == "runtime failed"
