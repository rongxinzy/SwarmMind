"""Artifact file resolution and response helpers."""

from __future__ import annotations

import mimetypes
import os
import re
from pathlib import Path
from urllib.parse import quote

from fastapi import HTTPException
from fastapi.responses import FileResponse, PlainTextResponse, Response

VIRTUAL_PATH_PREFIX = "/mnt/user-data"
ACTIVE_CONTENT_MIME_TYPES = {
    "text/html",
    "application/xhtml+xml",
    "image/svg+xml",
}
_SAFE_THREAD_ID_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


def normalize_virtual_path(path: str | None) -> str | None:
    """Normalize a sandbox virtual path to a leading-slash form."""
    if not path:
        return None

    stripped = path.strip().lstrip("/")
    if not stripped:
        return None
    return f"/{stripped}"


def is_virtual_user_data_path(path: str | None) -> bool:
    """Return whether a path points at the DeerFlow user-data mount."""
    normalized = normalize_virtual_path(path)
    return normalized == VIRTUAL_PATH_PREFIX or bool(normalized and normalized.startswith(f"{VIRTUAL_PATH_PREFIX}/"))


def _runtime_home() -> Path:
    configured = os.environ.get("DEER_FLOW_HOME")
    if configured:
        return Path(configured).resolve()
    return Path(__file__).resolve().parents[2] / ".runtime" / "deerflow" / "local-default" / "home"


def _validate_thread_id(thread_id: str) -> None:
    if not thread_id or not _SAFE_THREAD_ID_RE.match(thread_id):
        raise HTTPException(status_code=400, detail="Invalid thread_id")


def resolve_virtual_artifact_path(thread_id: str, virtual_path: str) -> Path:
    """Resolve a DeerFlow sandbox virtual path to a host path under the thread."""
    _validate_thread_id(thread_id)

    normalized = normalize_virtual_path(virtual_path)
    if not normalized or not is_virtual_user_data_path(normalized):
        raise HTTPException(status_code=400, detail=f"Path must start with {VIRTUAL_PATH_PREFIX}")

    relative = normalized.removeprefix(VIRTUAL_PATH_PREFIX).lstrip("/")
    user_data_dir = (_runtime_home() / "threads" / thread_id / "user-data").resolve()
    actual_path = (user_data_dir / relative).resolve()

    try:
        actual_path.relative_to(user_data_dir)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: path traversal detected") from None

    return actual_path


def build_content_disposition(disposition_type: str, filename: str) -> str:
    """Build an RFC 5987 encoded Content-Disposition header value."""
    return f"{disposition_type}; filename*=UTF-8''{quote(filename)}"


def build_attachment_headers(filename: str, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
    """Build attachment response headers for a filename."""
    headers = {"Content-Disposition": build_content_disposition("attachment", filename)}
    if extra_headers:
        headers.update(extra_headers)
    return headers


def is_text_file_by_content(path: Path, sample_size: int = 8192) -> bool:
    """Check if file content looks text-like."""
    try:
        with path.open("rb") as handle:
            return b"\x00" not in handle.read(sample_size)
    except OSError:
        return False


def build_artifact_file_response(actual_path: Path, download: bool = False) -> Response:
    """Build a safe response for a resolved artifact file."""
    if not actual_path.exists():
        raise HTTPException(status_code=404, detail="Artifact file not found")
    if not actual_path.is_file():
        raise HTTPException(status_code=400, detail="Artifact path is not a file")

    mime_type, _ = mimetypes.guess_type(actual_path)

    if download or mime_type in ACTIVE_CONTENT_MIME_TYPES:
        return FileResponse(
            path=actual_path,
            filename=actual_path.name,
            media_type=mime_type,
            headers=build_attachment_headers(actual_path.name),
        )

    if mime_type and mime_type.startswith("text/"):
        return PlainTextResponse(content=actual_path.read_text(encoding="utf-8"), media_type=mime_type)

    if is_text_file_by_content(actual_path):
        return PlainTextResponse(content=actual_path.read_text(encoding="utf-8"), media_type=mime_type or "text/plain")

    return Response(
        content=actual_path.read_bytes(),
        media_type=mime_type or "application/octet-stream",
        headers={"Content-Disposition": build_content_disposition("inline", actual_path.name)},
    )
