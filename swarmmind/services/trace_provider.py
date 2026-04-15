"""Trace checkpoint provider abstractions."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

from swarmmind.services.trace_checkpoint_storage import (
    LEGACY_DEFAULT_CHECKPOINTER_PATH as STORAGE_LEGACY_DEFAULT_CHECKPOINTER_PATH,
)
from swarmmind.services.trace_checkpoint_storage import (
    SqliteTraceCheckpointStorage,
    TraceCheckpointStorage,
)

logger = logging.getLogger(__name__)
LEGACY_DEFAULT_CHECKPOINTER_PATH = STORAGE_LEGACY_DEFAULT_CHECKPOINTER_PATH


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
        storage: TraceCheckpointStorage | None = None,
        provider_logger: logging.Logger = logger,
    ) -> None:
        self._storage = storage or SqliteTraceCheckpointStorage(checkpointer_path=checkpointer_path, storage_logger=provider_logger)
        self.checkpointer_path = self._storage.checkpointer_path
        self._logger = provider_logger

    def load_checkpoints(self, thread_id: str) -> list[dict[str, Any]]:
        """Load parsed checkpoints from upstream storage."""
        checkpoints: list[dict[str, Any]] = []
        for row in self._storage.fetch_checkpoint_rows(thread_id):
            parsed_row = self._parse_checkpoint_row(row)
            if parsed_row is not None:
                checkpoints.append(parsed_row)
        return checkpoints

    def _parse_checkpoint_row(self, row: Mapping[str, Any]) -> dict[str, Any] | None:
        """Decode one raw storage row into the trace checkpoint shape."""
        checkpoint_id = row["checkpoint_id"]
        checkpoint_payload = row["checkpoint"]
        metadata_payload = row["metadata"]

        try:
            checkpoint_data = json.loads(checkpoint_payload) if checkpoint_payload else {}
            metadata = json.loads(metadata_payload) if metadata_payload else {}
        except json.JSONDecodeError as exc:
            self._logger.warning("Failed to parse checkpoint %s: %s", checkpoint_id, exc)
            return None

        return {
            "thread_id": row["thread_id"],
            "checkpoint_id": checkpoint_id,
            "parent_checkpoint_id": row["parent_checkpoint_id"],
            "type": row["type"],
            "checkpoint": checkpoint_data,
            "metadata": metadata,
        }
