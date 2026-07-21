"""Approval request API is intentionally out of the current main path."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from swarmmind.api.supervisor import app
from swarmmind.db import dispose_engines, init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "approval_api_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    dispose_engines()
    init_db()


class TestApprovalRequestEndpoints:
    """Approval CRUD remains Phase C scaffolding, not a mounted API surface."""

    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("GET", "/approvals"),
            ("POST", "/approvals"),
            ("GET", "/approvals/nonexistent"),
            ("PATCH", "/approvals/nonexistent"),
            ("DELETE", "/approvals/nonexistent"),
        ],
    )
    def test_approval_endpoints_are_not_mounted(self, method: str, path: str):
        response = client.request(method, path, json={} if method in {"POST", "PATCH"} else None)

        assert response.status_code == 404
