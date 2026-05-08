"""Conversation promotion, artifact extraction, trace, and artifact serving routes."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from swarmmind.api.routers.mappers import db_to_artifact, db_to_project
from swarmmind.models import (
    ArtifactListResponse,
    ExtractArtifactsResponse,
    Project,
    PromoteConversationRequest,
    TraceSummaryResponse,
)
from swarmmind.services.artifact_content import (
    build_artifact_file_response,
    resolve_virtual_artifact_path,
)

logger = logging.getLogger(__name__)

NEW_CONVERSATION_TITLE = "New Conversation"


@dataclass(frozen=True)
class PromotionsRouterDeps:
    conversation_repo: object
    message_repo: object
    project_repo: object
    project_team_repo: object
    agent_team_repo: object
    artifact_repo: object
    # Callable[[], service] so tests can monkeypatch the module-level attribute and
    # have route handlers pick up the new value without rebuilding the router.
    message_trace_service_fn: object
    runtime_support: object


def build_promotions_router(deps: PromotionsRouterDeps) -> APIRouter:
    router = APIRouter()

    def _db_to_project(proj) -> Project:
        return db_to_project(proj, deps.project_team_repo, deps.agent_team_repo)

    def _ensure_project_conversation(project_id: str) -> str:
        from swarmmind.db import session_scope
        from swarmmind.db_models import ProjectDB

        proj = deps.project_repo.get_by_id(project_id)
        if proj.conversation_id:
            return proj.conversation_id
        conv = deps.conversation_repo.create(title=proj.title, title_status="pending")
        with session_scope() as session:
            proj_db = session.get(ProjectDB, project_id)
            if proj_db is not None:
                proj_db.conversation_id = conv.id
                session.commit()
        return conv.id

    def _attach_team(project_id: str, team_template_id: str | None) -> None:
        if team_template_id:
            try:
                deps.agent_team_repo.get_by_id(team_template_id)
                deps.project_team_repo.create(
                    project_id=project_id,
                    team_template_id=team_template_id,
                )
            except Exception as e:
                logger.warning("Failed to attach team %s to project %s: %s", team_template_id, project_id, e)

    def _generate_project_seed(conversation_id: str, override: PromoteConversationRequest | None) -> dict:
        conv = deps.conversation_repo.get_by_id(conversation_id)
        messages = deps.message_repo.list_by_conversation(conversation_id)
        user_msgs = [m for m in messages if m.role == "user"]
        assistant_msgs = [m for m in messages if m.role == "assistant"]

        title = override.title if override and override.title else conv.title
        if title in ("New Conversation", NEW_CONVERSATION_TITLE) and user_msgs:
            first_user = user_msgs[0].content.strip()
            title = first_user[:50] if len(first_user) <= 50 else first_user[:47] + "..."

        goal = override.goal if override and override.goal else None
        if goal is None and user_msgs:
            parts = [m.content.strip() for m in user_msgs[:3]]
            goal = "\n".join(parts)
            if len(goal) > 2000:
                goal = goal[:1997] + "..."

        scope = override.scope if override and override.scope else None
        constraints = override.constraints if override and override.constraints else None

        next_step = override.next_step if override and override.next_step else None
        if next_step is None and assistant_msgs:
            last = assistant_msgs[-1].content.strip()
            sentence_end = max(last.find("."), last.find("。"), last.find("\n"))
            if sentence_end > 0:
                next_step = last[: sentence_end + 1]
            else:
                next_step = last[:100] + "..." if len(last) > 100 else last

        return {
            "title": title or "Untitled Project",
            "goal": goal,
            "scope": scope,
            "constraints": constraints,
            "source_conversation_id": conversation_id,
            "next_step": next_step,
        }

    # ---- Routes ----

    @router.post(
        "/conversations/{conversation_id}/promote",
        tags=["conversations"],
        responses={404: {"description": "Conversation not found"}},
    )
    def promote_conversation(
        conversation_id: str,
        body: PromoteConversationRequest | None = None,
    ) -> Project:
        """Promote a ChatSession to a formal Project."""
        deps.conversation_repo.get_by_id(conversation_id)
        try:
            seed = _generate_project_seed(conversation_id, override=body)
        except Exception as e:
            logger.error("Project seed generation failed for %s: %s", conversation_id, e)
            seed = {
                "title": "Project from conversation",
                "goal": None,
                "scope": None,
                "constraints": None,
                "source_conversation_id": conversation_id,
                "next_step": "Review the source conversation and define next steps.",
            }

        proj = deps.project_repo.create(**seed)
        deps.project_repo.link_conversation(proj.project_id, conversation_id)
        _ensure_project_conversation(proj.project_id)
        _attach_team(proj.project_id, body.team_template_id if body else None)

        logger.info(
            "Conversation %s promoted to project %s (%s)",
            conversation_id,
            proj.project_id,
            proj.title,
        )
        return _db_to_project(proj)

    @router.get(
        "/conversations/{conversation_id}/messages/{message_id}/trace",
        tags=["conversations"],
        responses={404: {"description": "Conversation or message not found"}},
    )
    def get_message_trace(conversation_id: str, message_id: str) -> TraceSummaryResponse:
        """Return a readable trace summary for an assistant message."""
        deps.conversation_repo.get_by_id(conversation_id)
        msg = deps.message_repo.get_by_id(message_id)
        if msg.conversation_id != conversation_id:
            raise HTTPException(status_code=404, detail="Message not found in this conversation")
        try:
            return deps.message_trace_service_fn().get_summary(conversation_id, message_id)
        except Exception as exc:
            logger.warning("Trace summary failed for message %s: %s", message_id, exc)
            summary = "执行完成" if msg.run_id else "直接回复"
            return TraceSummaryResponse(
                steps_count=1 if msg.run_id else 0,
                subagent_calls_count=0,
                artifacts_count=0,
                blocked_points=[],
                summary=summary,
            )

    @router.get(
        "/conversations/{conversation_id}/artifacts",
        tags=["conversations"],
        responses={404: {"description": "Conversation not found"}},
    )
    def list_conversation_artifacts(conversation_id: str) -> ArtifactListResponse:
        """List artifacts for a conversation."""
        deps.conversation_repo.get_by_id(conversation_id)
        rows = deps.artifact_repo.list_by_conversation(conversation_id)
        return ArtifactListResponse(items=[db_to_artifact(r) for r in rows], total=len(rows))

    @router.get(
        "/conversations/{conversation_id}/artifacts/{artifact_path:path}",
        tags=["conversations"],
        responses={
            400: {"description": "Invalid artifact path"},
            403: {"description": "Artifact path escapes the conversation sandbox"},
            404: {"description": "Conversation or artifact not found"},
        },
    )
    def get_conversation_artifact_file(
        conversation_id: str, artifact_path: str, download: bool = False
    ) -> Response:
        """Return the registered artifact file content for a conversation."""
        conversation = deps.conversation_repo.get_by_id(conversation_id)
        artifact = deps.artifact_repo.get_by_conversation_path(conversation_id, artifact_path)
        virtual_path = artifact.path or artifact.name or artifact_path
        thread_id = conversation.thread_id or deps.runtime_support.conversation_thread_id(conversation_id)
        actual_path = resolve_virtual_artifact_path(thread_id, virtual_path)
        return build_artifact_file_response(actual_path, download=download)

    @router.post(
        "/conversations/{conversation_id}/extract-artifacts",
        tags=["conversations"],
        responses={404: {"description": "Conversation not found"}},
    )
    def extract_conversation_artifacts(conversation_id: str) -> ExtractArtifactsResponse:
        """Extract artifacts from conversation trace and persist them. Idempotent."""
        conv = deps.conversation_repo.get_by_id(conversation_id)
        project_id = conv.promoted_project_id if conv else None
        created = deps.message_trace_service_fn().extract_artifacts(conversation_id, project_id=project_id)
        return ExtractArtifactsResponse(conversation_id=conversation_id, extracted=len(created), artifacts=created)

    return router
