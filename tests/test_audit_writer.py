"""Tests for swarmmind.services.audit_writer."""

from unittest.mock import MagicMock, patch

from swarmmind.services.audit_writer import AuditWriter


class TestAuditWriter:
    def setup_method(self):
        self.repo = MagicMock()
        self.writer = AuditWriter(audit_log_repo=self.repo)

    def test_write_delegates_to_repo(self):
        self.writer.write(
            event_type="run.started",
            project_id="proj-1",
            run_id="run-1",
        )
        self.repo.create.assert_called_once_with(
            audit_type="run.started",
            project_id="proj-1",
            run_id="run-1",
            approval_id=None,
            actor_id="system",
            actor_type="system",
            decision=None,
            reason=None,
            extra_data=None,
        )

    def test_write_with_all_fields(self):
        self.writer.write(
            event_type="approval.decided",
            project_id="proj-2",
            run_id="run-2",
            approval_id="ap-1",
            actor="alice",
            actor_type="user",
            decision="approved",
            reason="LGTM",
            evidence={"tool": "shell"},
        )
        self.repo.create.assert_called_once_with(
            audit_type="approval.decided",
            project_id="proj-2",
            run_id="run-2",
            approval_id="ap-1",
            actor_id="alice",
            actor_type="user",
            decision="approved",
            reason="LGTM",
            extra_data={"tool": "shell"},
        )

    def test_write_returns_created_entry(self):
        fake_entry = MagicMock()
        self.repo.create.return_value = fake_entry
        result = self.writer.write(event_type="run.completed", project_id="p")
        assert result is fake_entry

    def test_write_swallows_repo_exception(self):
        self.repo.create.side_effect = RuntimeError("DB error")
        # Should not raise
        result = self.writer.write(event_type="run.started", project_id="proj-1")
        assert result is None

    def test_write_logs_on_exception(self):
        self.repo.create.side_effect = ValueError("bad data")
        with patch("swarmmind.services.audit_writer.logger") as mock_logger:
            self.writer.write(event_type="run.started", project_id="proj-1")
        mock_logger.exception.assert_called_once()
        assert "AuditWriter.write failed" in mock_logger.exception.call_args[0][0]
