"""Time helpers for SwarmMind persistence and API layers."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current UTC time as a naive datetime for schema compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)
