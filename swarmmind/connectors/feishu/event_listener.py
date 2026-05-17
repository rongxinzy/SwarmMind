"""Feishu event listener: subscribes to Feishu bot events and dispatches to SwarmMind."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from collections.abc import AsyncIterator
from typing import Any

from swarmmind.connectors.feishu.cli_runner import LarkCLINotFoundError, check_lark_cli

logger = logging.getLogger(__name__)

# Feishu event types we handle
_INGEST_EVENT_TYPES = {
    "im.message.receive_v1",
    "im.message.recalled_v1",
}


class FeishuEventListener:
    """Subscribes to Feishu events via lark-cli and dispatches them to SwarmMind.

    Runs ``lark-cli event +listen --format ndjson`` as a long-lived subprocess,
    reads NDJSON lines, and translates message events into SwarmMind API calls.

    Args:
        api_url: SwarmMind supervisor API base URL.
        api_token: Bearer token for SwarmMind API (optional).
        bot_name: Bot display name used to filter @mentions (optional).
        default_project_id: SwarmMind project to associate messages with (optional).
    """

    def __init__(
        self,
        api_url: str,
        api_token: str | None = None,
        bot_name: str = "",
        default_project_id: str = "",
    ) -> None:
        """Initialize the event listener."""
        self._api_url = api_url.rstrip("/")
        self._api_token = api_token
        self._bot_name = bot_name
        self._default_project_id = default_project_id
        self._process: asyncio.subprocess.Process | None = None
        self._running = False

    async def _event_stream(self) -> AsyncIterator[dict[str, Any]]:
        """Yield parsed NDJSON events from lark-cli event +listen."""
        cli_path = check_lark_cli()
        cmd = [cli_path, "event", "+listen", "--format", "ndjson"]

        logger.info("Starting Feishu event stream: %s", " ".join(cmd))
        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        assert self._process.stdout is not None  # noqa: S101
        async for line_bytes in self._process.stdout:
            line = line_bytes.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                if isinstance(event, dict):
                    yield event
            except json.JSONDecodeError:
                logger.debug("Unparseable event line: %s", line)

    async def _dispatch_to_swarmmind(self, event: dict[str, Any]) -> None:
        """Translate a Feishu event into a SwarmMind API call."""
        import httpx

        event_type = event.get("event_type", "")
        if event_type not in _INGEST_EVENT_TYPES:
            return

        # Extract message text
        message = event.get("event", {}).get("message", {})
        msg_type = message.get("message_type", "")
        if msg_type != "text":
            logger.debug("Ignoring non-text message type: %s", msg_type)
            return

        try:
            body = json.loads(message.get("content", "{}"))
            text = body.get("text", "").strip()
        except (json.JSONDecodeError, AttributeError):
            return

        if not text:
            return

        # Strip @bot mention if present
        if self._bot_name and text.startswith(f"@{self._bot_name}"):
            text = text[len(self._bot_name) + 1:].strip()

        chat_id = message.get("chat_id", "")
        message_id = message.get("message_id", "")

        logger.info("Received Feishu message [%s] from chat %s: %s", message_id, chat_id, text[:80])

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_token:
            headers["Authorization"] = f"Bearer {self._api_token}"

        async with httpx.AsyncClient(base_url=self._api_url, headers=headers, timeout=60.0) as client:
            try:
                if self._default_project_id:
                    # Route to a fixed project
                    resp = await client.post(
                        f"/projects/{self._default_project_id}/messages/stream",
                        json={"content": text},
                    )
                else:
                    # Free-form dispatch
                    resp = await client.post("/dispatch", json={"goal": text})

                resp.raise_for_status()
                result = resp.json()
                reply = _extract_reply(result)
            except httpx.HTTPError as exc:
                logger.error("SwarmMind API error for message %s: %s", message_id, exc)
                reply = "Sorry, I encountered an error processing your request."

        if reply and chat_id:
            await self._send_reply(chat_id, reply)

    async def _send_reply(self, chat_id: str, content: str) -> None:
        """Post a reply to a Feishu chat via lark-cli."""
        from swarmmind.connectors.feishu.cli_runner import LarkCLIError, run_lark_cli

        try:
            run_lark_cli("im", "message", "+send", "--chat-id", chat_id, "--content", content)
        except (LarkCLIError, LarkCLINotFoundError) as exc:
            logger.error("Failed to send reply to Feishu chat %s: %s", chat_id, exc)

    async def run(self) -> None:
        """Run the event listener until stopped or until lark-cli exits."""
        self._running = True
        try:
            check_lark_cli()
        except LarkCLINotFoundError as exc:
            logger.error("%s", exc)
            sys.exit(1)

        while self._running:
            try:
                async for event in self._event_stream():
                    if not self._running:
                        break
                    await self._dispatch_to_swarmmind(event)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("Event stream error: %s — restarting in 5s", exc)
                await asyncio.sleep(5)

        await self.stop()

    async def stop(self) -> None:
        """Terminate the lark-cli subprocess."""
        self._running = False
        if self._process and self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()


def _extract_reply(result: dict[str, Any]) -> str:
    """Extract a human-readable reply from a SwarmMind API response."""
    # dispatch response
    if "response" in result:
        return str(result["response"])
    # chat send_message response
    if "content" in result:
        return str(result["content"])
    # minimal fallback
    return json.dumps(result, ensure_ascii=False)
