"""Artifact API endpoint tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from swarmmind.api import supervisor
from swarmmind.api.supervisor import app
from swarmmind.db import dispose_engines, init_db
from swarmmind.repositories.artifact import ArtifactRepository
from swarmmind.repositories.conversation import ConversationRepository
from swarmmind.repositories.project import ProjectRepository
from swarmmind.repositories.run import RunRepository
from swarmmind.repositories.task import TaskRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "artifact_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    dispose_engines()
    init_db()


class TestArtifactEndpoints:
    """Artifact REST API tests."""

    def test_list_artifacts_empty(self):
        conv_repo = ConversationRepository()
        conv = conv_repo.create("Chat", "pending")

        response = client.get(f"/conversations/{conv.id}/artifacts")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_artifacts_with_items(self):
        conv_repo = ConversationRepository()
        art_repo = ArtifactRepository()
        conv = conv_repo.create("Chat", "pending")
        art_repo.create(
            conv.id, None, "/mnt/user-data/outputs/report.md", "write_file", mime_type="text/markdown", size_bytes=123
        )
        art_repo.create(conv.id, None, "plan.md", "present_files")

        response = client.get(f"/conversations/{conv.id}/artifacts")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        names = {a["name"] for a in data["items"]}
        assert names == {"/mnt/user-data/outputs/report.md", "plan.md"}
        report = next(a for a in data["items"] if a["name"] == "/mnt/user-data/outputs/report.md")
        assert report["path"] == "/mnt/user-data/outputs/report.md"
        assert report["mime_type"] == "text/markdown"
        assert report["size_bytes"] == 123
        plan = next(a for a in data["items"] if a["name"] == "plan.md")
        assert plan["path"] is None

    def test_list_artifacts_conversation_not_found(self):
        response = client.get("/conversations/nonexistent/artifacts")
        assert response.status_code == 404

    def test_extract_artifacts_from_trace(self, monkeypatch):
        conv_repo = ConversationRepository()
        conv = conv_repo.create("Chat", "pending")

        mock_svc = MagicMock()
        mock_svc.extract_artifacts.return_value = [
            {"artifact_id": "art-1", "name": "output.md", "artifact_type": "write_file"},
        ]
        monkeypatch.setattr(supervisor, "message_trace_service", mock_svc)

        response = client.post(f"/conversations/{conv.id}/extract-artifacts")
        assert response.status_code == 200
        data = response.json()
        assert data["extracted"] == 1
        assert data["artifacts"][0]["name"] == "output.md"
        mock_svc.extract_artifacts.assert_called_once_with(conv.id, project_id=None)

    def test_extract_artifacts_conversation_not_found(self):
        response = client.post("/conversations/nonexistent/extract-artifacts")
        assert response.status_code == 404

    def test_extract_artifacts_empty(self, monkeypatch):
        conv_repo = ConversationRepository()
        conv = conv_repo.create("Chat", "pending")

        mock_svc = MagicMock()
        mock_svc.extract_artifacts.return_value = []
        monkeypatch.setattr(supervisor, "message_trace_service", mock_svc)

        response = client.post(f"/conversations/{conv.id}/extract-artifacts")
        assert response.status_code == 200
        data = response.json()
        assert data["extracted"] == 0

    def test_list_artifacts_with_trace_fields(self):
        conv_repo = ConversationRepository()
        art_repo = ArtifactRepository()
        run_repo = RunRepository()
        proj_repo = ProjectRepository()
        task_repo = TaskRepository()

        conv = conv_repo.create("Chat", "pending")
        run = run_repo.create(conversation_id=conv.id)
        proj = proj_repo.create(title="Test Project")
        task = task_repo.create(project_id=proj.project_id, title="Test Task")

        art_repo.create(
            conv.id,
            None,
            "report.md",
            "write_file",
            run_id=run.run_id,
            task_id=task.task_id,
            author_role="产品专家",
        )

        response = client.get(f"/conversations/{conv.id}/artifacts")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["name"] == "report.md"
        assert item["run_id"] == run.run_id
        assert item["task_id"] == task.task_id
        assert item["author_role"] == "产品专家"

    def test_get_artifact_file_text(self, monkeypatch, tmp_path):
        conv_repo = ConversationRepository()
        art_repo = ArtifactRepository()
        conv = conv_repo.create("Chat", "pending")

        deer_home = tmp_path / "deer-home"
        output_dir = deer_home / "threads" / conv.id / "user-data" / "outputs"
        output_dir.mkdir(parents=True)
        artifact_file = output_dir / "report.md"
        artifact_file.write_text("# Report\n\nDone.", encoding="utf-8")
        monkeypatch.setenv("DEER_FLOW_HOME", str(deer_home))

        art_repo.create(
            conversation_id=conv.id,
            name="/mnt/user-data/outputs/report.md",
            artifact_type="write_file",
        )

        response = client.get(f"/conversations/{conv.id}/artifacts/mnt/user-data/outputs/report.md")
        assert response.status_code == 200
        assert response.text == "# Report\n\nDone."
        assert response.headers["content-type"].startswith("text/markdown")

    def test_get_artifact_file_download_for_active_content(self, monkeypatch, tmp_path):
        conv_repo = ConversationRepository()
        art_repo = ArtifactRepository()
        conv = conv_repo.create("Chat", "pending")

        deer_home = tmp_path / "deer-home"
        output_dir = deer_home / "threads" / conv.id / "user-data" / "outputs"
        output_dir.mkdir(parents=True)
        (output_dir / "chart.svg").write_text("<svg></svg>", encoding="utf-8")
        monkeypatch.setenv("DEER_FLOW_HOME", str(deer_home))

        art_repo.create(
            conversation_id=conv.id,
            name="/mnt/user-data/outputs/chart.svg",
            artifact_type="write_file",
        )

        response = client.get(f"/conversations/{conv.id}/artifacts/mnt/user-data/outputs/chart.svg")
        assert response.status_code == 200
        assert response.headers["content-disposition"].startswith("attachment;")

    def test_get_skill_artifact_preview_entry(self, monkeypatch, tmp_path):
        conv_repo = ConversationRepository()
        art_repo = ArtifactRepository()
        conv = conv_repo.create("Chat", "pending")

        deer_home = tmp_path / "deer-home"
        skill_dir = deer_home / "threads" / conv.id / "user-data" / "outputs" / "research.skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Research Skill\n\nUse this skill.", encoding="utf-8")
        monkeypatch.setenv("DEER_FLOW_HOME", str(deer_home))

        art_repo.create(
            conversation_id=conv.id,
            name="/mnt/user-data/outputs/research.skill",
            artifact_type="present_files",
        )

        response = client.get(f"/conversations/{conv.id}/artifacts/mnt/user-data/outputs/research.skill/SKILL.md")
        assert response.status_code == 200
        assert response.text == "# Research Skill\n\nUse this skill."
        assert response.headers["content-type"].startswith("text/markdown")

    def test_get_skill_artifact_preview_rejects_escape(self, monkeypatch, tmp_path):
        conv_repo = ConversationRepository()
        art_repo = ArtifactRepository()
        conv = conv_repo.create("Chat", "pending")

        deer_home = tmp_path / "deer-home"
        output_dir = deer_home / "threads" / conv.id / "user-data" / "outputs"
        skill_dir = output_dir / "research.skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Research Skill", encoding="utf-8")
        (output_dir / "secret.txt").write_text("hidden", encoding="utf-8")
        monkeypatch.setenv("DEER_FLOW_HOME", str(deer_home))

        art_repo.create(
            conversation_id=conv.id,
            name="/mnt/user-data/outputs/research.skill",
            artifact_type="present_files",
        )

        response = client.get(f"/conversations/{conv.id}/artifacts/mnt/user-data/outputs/research.skill/%2E%2E/secret.txt")
        assert response.status_code == 403

    def test_get_html_artifact_bundle_asset(self, monkeypatch, tmp_path):
        conv_repo = ConversationRepository()
        art_repo = ArtifactRepository()
        conv = conv_repo.create("Chat", "pending")

        deer_home = tmp_path / "deer-home"
        site_dir = deer_home / "threads" / conv.id / "user-data" / "outputs" / "site"
        site_dir.mkdir(parents=True)
        (site_dir / "index.html").write_text('<link rel="stylesheet" href="style.css">', encoding="utf-8")
        (site_dir / "style.css").write_text("body { color: black; }", encoding="utf-8")
        monkeypatch.setenv("DEER_FLOW_HOME", str(deer_home))

        art_repo.create(
            conversation_id=conv.id,
            name="/mnt/user-data/outputs/site/index.html",
            artifact_type="present_files",
            mime_type="text/html",
        )

        response = client.get(f"/conversations/{conv.id}/artifacts/mnt/user-data/outputs/site/style.css")
        assert response.status_code == 200
        assert response.text == "body { color: black; }"
        assert response.headers["content-type"].startswith("text/css")

    def test_get_html_artifact_bundle_rejects_escape(self, monkeypatch, tmp_path):
        conv_repo = ConversationRepository()
        art_repo = ArtifactRepository()
        conv = conv_repo.create("Chat", "pending")

        deer_home = tmp_path / "deer-home"
        output_dir = deer_home / "threads" / conv.id / "user-data" / "outputs"
        site_dir = output_dir / "site"
        site_dir.mkdir(parents=True)
        (site_dir / "index.html").write_text("<html></html>", encoding="utf-8")
        (output_dir / "secret.css").write_text("hidden", encoding="utf-8")
        monkeypatch.setenv("DEER_FLOW_HOME", str(deer_home))

        art_repo.create(
            conversation_id=conv.id,
            name="/mnt/user-data/outputs/site/index.html",
            artifact_type="present_files",
            mime_type="text/html",
        )

        response = client.get(f"/conversations/{conv.id}/artifacts/mnt/user-data/outputs/site/%2E%2E/secret.css")
        assert response.status_code == 403

    def test_get_artifact_file_requires_registered_artifact(self, monkeypatch, tmp_path):
        conv_repo = ConversationRepository()
        conv = conv_repo.create("Chat", "pending")

        deer_home = tmp_path / "deer-home"
        output_dir = deer_home / "threads" / conv.id / "user-data" / "outputs"
        output_dir.mkdir(parents=True)
        (output_dir / "unregistered.md").write_text("hidden", encoding="utf-8")
        monkeypatch.setenv("DEER_FLOW_HOME", str(deer_home))

        response = client.get(f"/conversations/{conv.id}/artifacts/mnt/user-data/outputs/unregistered.md")
        assert response.status_code == 404

    def test_get_artifact_file_rejects_path_traversal(self, monkeypatch, tmp_path):
        conv_repo = ConversationRepository()
        art_repo = ArtifactRepository()
        conv = conv_repo.create("Chat", "pending")

        deer_home = tmp_path / "deer-home"
        monkeypatch.setenv("DEER_FLOW_HOME", str(deer_home))
        art_repo.create(
            conversation_id=conv.id,
            name="/mnt/user-data/../secret.txt",
            artifact_type="write_file",
        )

        response = client.get(f"/conversations/{conv.id}/artifacts/mnt/user-data/%2E%2E/secret.txt")
        assert response.status_code == 403

    def test_upload_file_registers_user_data_artifact(self, monkeypatch, tmp_path):
        conv_repo = ConversationRepository()
        conv = conv_repo.create("Chat", "pending")

        deer_home = tmp_path / "deer-home"
        monkeypatch.setenv("DEER_FLOW_HOME", str(deer_home))

        response = client.post(
            f"/api/threads/{conv.id}/uploads",
            files=[("files", ("brief.txt", b"hello upload", "text/plain"))],
        )

        assert response.status_code == 200
        data = response.json()
        uploaded = data["files"][0]
        assert uploaded["filename"] == "brief.txt"
        assert uploaded["size"] == len(b"hello upload")
        assert uploaded["virtual_path"] == "/mnt/user-data/uploads/brief.txt"
        assert (deer_home / "threads" / conv.id / "user-data" / "uploads" / "brief.txt").read_text(
            encoding="utf-8"
        ) == "hello upload"

        artifact_response = client.get(f"/conversations/{conv.id}/artifacts/mnt/user-data/uploads/brief.txt")
        assert artifact_response.status_code == 200
        assert artifact_response.text == "hello upload"
