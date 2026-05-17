"""Subprocess runner for lark-cli commands."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any


class LarkCLINotFoundError(RuntimeError):
    """Raised when lark-cli is not installed or not on PATH."""


class LarkCLIError(RuntimeError):
    """Raised when a lark-cli command exits with a non-zero return code."""

    def __init__(self, message: str, returncode: int, stderr: str) -> None:
        """Initialize with message, return code, and stderr output."""
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


def check_lark_cli() -> str:
    """Return the path to lark-cli, or raise LarkCLINotFoundError."""
    path = shutil.which("lark-cli")
    if path is None:
        raise LarkCLINotFoundError(
            "lark-cli not found on PATH. Install it with:\n"
            "  npx @larksuite/cli@latest install\n"
            "Then authenticate:\n"
            "  lark-cli config init\n"
            "  lark-cli auth login --recommend"
        )
    return path


def run_lark_cli(
    *args: str,
    timeout: int = 30,
    output_format: str = "json",
) -> Any:
    """Run a lark-cli command and return parsed output.

    Args:
        *args: Command arguments after ``lark-cli`` (e.g. ``"im", "message", "+send"``).
        timeout: Subprocess timeout in seconds.
        output_format: Output format flag passed to lark-cli (``"json"`` or ``"ndjson"``).

    Returns:
        Parsed JSON output (dict or list), or the raw string if unparsable.

    Raises:
        LarkCLINotFoundError: lark-cli is not installed.
        LarkCLIError: The command exited with a non-zero return code.
    """
    cli_path = check_lark_cli()
    cmd = [cli_path, *args, "--format", output_format]

    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise LarkCLIError(
            f"lark-cli command timed out after {timeout}s: {' '.join(args)}",
            returncode=-1,
            stderr="",
        ) from exc

    if result.returncode != 0:
        raise LarkCLIError(
            f"lark-cli command failed (exit {result.returncode}): {result.stderr.strip()}",
            returncode=result.returncode,
            stderr=result.stderr,
        )

    stdout = result.stdout.strip()
    if not stdout:
        return {}

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"raw": stdout}


def run_lark_cli_ndjson(
    *args: str,
    timeout: int = 30,
) -> list[dict[str, Any]]:
    """Run a lark-cli command and return all NDJSON lines as a list."""
    cli_path = check_lark_cli()
    cmd = [cli_path, *args, "--format", "ndjson"]

    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise LarkCLIError(
            f"lark-cli command timed out after {timeout}s",
            returncode=-1,
            stderr="",
        ) from exc

    if result.returncode != 0:
        raise LarkCLIError(
            f"lark-cli command failed (exit {result.returncode}): {result.stderr.strip()}",
            returncode=result.returncode,
            stderr=result.stderr,
        )

    lines = []
    for raw_line in result.stdout.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        try:
            lines.append(json.loads(stripped))
        except json.JSONDecodeError:
            lines.append({"raw": stripped})
    return lines
