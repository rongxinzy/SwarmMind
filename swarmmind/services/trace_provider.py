"""Trace checkpoint provider abstractions."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)


LEGACY_DEFAULT_CHECKPOINTER_PATH = (
    Path(__file__).resolve().parents[2] / ".runtime" / "deerflow" / "local-default" / "checkpoints.db"
)
DEFAULT_CHECKPOINTER_FILENAME = "checkpoints.db"


def resolve_default_checkpointer_path() -> Path:
    """Resolve the default SqliteSaver path from runtime env when available."""
    deer_flow_home = os.environ.get("DEER_FLOW_HOME")
    if not deer_flow_home:
        return LEGACY_DEFAULT_CHECKPOINTER_PATH

    runtime_home = Path(deer_flow_home).expanduser()
    direct_candidate = runtime_home / DEFAULT_CHECKPOINTER_FILENAME
    sibling_candidate = runtime_home.parent / DEFAULT_CHECKPOINTER_FILENAME

    for candidate in (direct_candidate, sibling_candidate):
        if candidate.exists():
            return candidate

    if runtime_home.name == "home":
        return sibling_candidate

    return direct_candidate


class TraceCheckpointProvider(Protocol):
    """Loads raw checkpoints for a conversation thread."""

    checkpointer_path: Path | None

    def load_checkpoints(self, thread_id: str) -> list[dict[str, Any]]:
        """Load raw checkpoints for a thread."""


class SqliteTraceCheckpointProvider:
    """Trace checkpoint provider backed by langgraph/deer-flow SqliteSaver data."""

    def __init__(
        self,
        checkpointer_path: Path | str | None = None,
        connect_fn: Callable[..., sqlite3.Connection] = sqlite3.connect,
        provider_logger: logging.Logger = logger,
    ) -> None:
        self.checkpointer_path = Path(checkpointer_path) if checkpointer_path else resolve_default_checkpointer_path()
        self._connect_fn = connect_fn
        self._logger = provider_logger

    def load_checkpoints(self, thread_id: str) -> list[dict[str, Any]]:
        """Load checkpoints from a SqliteSaver database."""
        if not self.checkpointer_path.exists():
            self._logger.warning("Checkpointer database not found at %s", self.checkpointer_path)
            return []

        conn = self._connect_fn(self.checkpointer_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row

        try:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT thread_id, checkpoint_id, parent_checkpoint_id, type,
                           checkpoint, metadata
                    FROM checkpoints
                    WHERE thread_id = ? AND checkpoint_ns = ''
                    ORDER BY checkpoint_id ASC
                    """,
                    (thread_id,),
                )
            except sqlite3.OperationalError as exc:
                self._logger.warning(
                    "Checkpoint query failed for thread %s at %s: %s",
                    thread_id,
                    self.checkpointer_path,
                    exc,
                )
                return []

            checkpoints: list[dict[str, Any]] = []
            for row in cursor.fetchall():
                try:
                    checkpoint_data = json.loads(row["checkpoint"]) if row["checkpoint"] else {}
                    metadata = json.loads(row["metadata"]) if row["metadata"] else {}
                except json.JSONDecodeError as exc:
                    self._logger.warning("Failed to parse checkpoint %s: %s", row["checkpoint_id"], exc)
                    continue

                checkpoints.append(
                    {
                        "thread_id": row["thread_id"],
                        "checkpoint_id": row["checkpoint_id"],
                        "parent_checkpoint_id": row["parent_checkpoint_id"],
                        "type": row["type"],
                        "checkpoint": checkpoint_data,
                        "metadata": metadata,
                    }
                )

            return checkpoints
        finally:
            conn.close()
