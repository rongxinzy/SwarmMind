"""Capability risk classification for the governance gate."""

from __future__ import annotations

import enum


class RiskTier(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Static capability → risk tier table.
# Keys are DeerFlow tool names (lowercased, dotted paths).
# Unknown capabilities default to LOW.
CAPABILITY_RISK: dict[str, RiskTier] = {
    # Shell / code execution — highest risk
    "shell": RiskTier.HIGH,
    "bash": RiskTier.HIGH,
    "execute_code": RiskTier.HIGH,
    "run_python": RiskTier.HIGH,
    "python_repl": RiskTier.HIGH,
    "tools.shell": RiskTier.HIGH,
    "tools.bash": RiskTier.HIGH,
    "tools.execute_code": RiskTier.HIGH,
    "tools.run_python": RiskTier.HIGH,
    # File writes
    "write_file": RiskTier.MEDIUM,
    "create_file": RiskTier.MEDIUM,
    "delete_file": RiskTier.HIGH,
    "tools.write_file": RiskTier.MEDIUM,
    "tools.create_file": RiskTier.MEDIUM,
    "tools.delete_file": RiskTier.HIGH,
    # External HTTP writes
    "http_post": RiskTier.MEDIUM,
    "http_put": RiskTier.MEDIUM,
    "http_patch": RiskTier.MEDIUM,
    "http_delete": RiskTier.HIGH,
    "tools.http_post": RiskTier.MEDIUM,
    "tools.http_put": RiskTier.MEDIUM,
    "tools.http_patch": RiskTier.MEDIUM,
    "tools.http_delete": RiskTier.HIGH,
    # Read-only — low risk
    "http_get": RiskTier.LOW,
    "read_file": RiskTier.LOW,
    "web_search": RiskTier.LOW,
    "search": RiskTier.LOW,
    "tools.http_get": RiskTier.LOW,
    "tools.read_file": RiskTier.LOW,
    "tools.web_search": RiskTier.LOW,
}


def classify(capability: str) -> RiskTier:
    """Return the risk tier for a capability name.

    Checks the exact name, then a normalised lowercase version.
    Unknown capabilities default to LOW so ordinary tools are not blocked.
    """
    if capability in CAPABILITY_RISK:
        return CAPABILITY_RISK[capability]
    normalized = capability.lower().strip()
    if normalized in CAPABILITY_RISK:
        return CAPABILITY_RISK[normalized]
    return RiskTier.LOW
