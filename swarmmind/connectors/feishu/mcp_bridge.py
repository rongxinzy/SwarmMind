"""FastMCP server that exposes lark-cli commands as MCP tools for DeerFlow agents."""

from __future__ import annotations

from typing import Any

from swarmmind.connectors.feishu.cli_runner import LarkCLIError, LarkCLINotFoundError, run_lark_cli


def build_feishu_mcp_server(port: int = 7070) -> Any:
    """Build and return a FastMCP server exposing Feishu tools.

    The server runs on ``http://0.0.0.0:{port}/mcp`` using streamable-http transport.
    Each tool wraps a ``lark-cli`` subprocess call; lark-cli handles its own
    authentication via the OS keychain.

    Args:
        port: TCP port for the MCP server.

    Returns:
        A configured FastMCP instance.

    Raises:
        RuntimeError: If the ``mcp`` optional dependency is not installed.
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ModuleNotFoundError as exc:
        raise RuntimeError("MCP support is not installed. Install with `pip install 'swarmmind[mcp]'`.") from exc

    mcp = FastMCP("feishu", port=port)

    def _run(*args: str, timeout: int = 30) -> dict[str, Any]:
        try:
            result = run_lark_cli(*args, timeout=timeout)
            if isinstance(result, dict):
                return result
            return {"data": result}
        except LarkCLINotFoundError as exc:
            return {"error": str(exc), "type": "lark_cli_not_found"}
        except LarkCLIError as exc:
            return {"error": str(exc), "type": "lark_cli_error", "returncode": exc.returncode}

    # ── Messaging (im) ──────────────────────────────────────────────────────────

    @mcp.tool()
    def feishu_send_message(
        chat_id: str,
        content: str,
        message_type: str = "text",
    ) -> dict[str, Any]:
        """Send a message to a Feishu chat (group or direct message).

        Args:
            chat_id: The chat ID (group chat or user open_id/union_id).
            content: Message content. For text, plain string. For rich_text, markdown.
            message_type: Message type: ``text``, ``post`` (rich text), or ``interactive``.
        """
        return _run("im", "message", "+send", "--chat-id", chat_id, "--content", content, "--type", message_type)

    @mcp.tool()
    def feishu_list_messages(chat_id: str, limit: int = 20) -> dict[str, Any]:
        """List recent messages in a Feishu chat.

        Args:
            chat_id: The chat ID to list messages from.
            limit: Maximum number of messages to return (default 20).
        """
        return _run("im", "message", "list", "--chat-id", chat_id, "--page-limit", str(limit))

    @mcp.tool()
    def feishu_get_chat_info(chat_id: str) -> dict[str, Any]:
        """Get metadata for a Feishu chat (name, members, type).

        Args:
            chat_id: The chat ID.
        """
        return _run("im", "chat", "get", "--chat-id", chat_id)

    @mcp.tool()
    def feishu_list_chats() -> dict[str, Any]:
        """List all Feishu chats the bot or user belongs to."""
        return _run("im", "chat", "list")

    # ── Documents (doc) ─────────────────────────────────────────────────────────

    @mcp.tool()
    def feishu_create_doc(title: str, content: str = "") -> dict[str, Any]:
        """Create a new Feishu document.

        Args:
            title: Document title.
            content: Initial document content in Markdown format.
        """
        args = ["doc", "documents", "create", "--title", title]
        if content:
            args += ["--content", content]
        return _run(*args)

    @mcp.tool()
    def feishu_get_doc(document_id: str) -> dict[str, Any]:
        """Get the content of a Feishu document.

        Args:
            document_id: The document token/ID.
        """
        return _run("doc", "documents", "get", "--document-id", document_id)

    @mcp.tool()
    def feishu_list_docs(folder_token: str = "") -> dict[str, Any]:
        """List documents in a Feishu folder.

        Args:
            folder_token: Folder token. Leave empty for the root folder.
        """
        args = ["doc", "documents", "list"]
        if folder_token:
            args += ["--folder-token", folder_token]
        return _run(*args)

    # ── Search ───────────────────────────────────────────────────────────────────

    @mcp.tool()
    def feishu_search(query: str, types: str = "docx,wiki,message") -> dict[str, Any]:
        """Search across Feishu content (docs, wiki, messages).

        Args:
            query: Search query string.
            types: Comma-separated list of content types to search.
                   Options: ``docx``, ``wiki``, ``message``, ``chat``.
        """
        return _run("search", "+query", "--query", query, "--types", types)

    # ── Calendar ─────────────────────────────────────────────────────────────────

    @mcp.tool()
    def feishu_get_agenda(date: str = "", days: int = 7) -> dict[str, Any]:
        """Get calendar agenda for upcoming days.

        Args:
            date: Start date in ISO 8601 format (e.g. ``2026-05-17``). Defaults to today.
            days: Number of days ahead to include (default 7).
        """
        args = ["calendar", "+agenda", "--days", str(days)]
        if date:
            args += ["--date", date]
        return _run(*args)

    @mcp.tool()
    def feishu_create_event(
        title: str,
        start_time: str,
        end_time: str,
        description: str = "",
        attendees: str = "",
    ) -> dict[str, Any]:
        """Create a calendar event in Feishu.

        Args:
            title: Event title.
            start_time: Start time in ISO 8601 format (e.g. ``2026-05-17T14:00:00+08:00``).
            end_time: End time in ISO 8601 format.
            description: Event description (optional).
            attendees: Comma-separated list of attendee emails or open_ids (optional).
        """
        args = [
            "calendar",
            "calendar_events",
            "create",
            "--title",
            title,
            "--start-time",
            start_time,
            "--end-time",
            end_time,
        ]
        if description:
            args += ["--description", description]
        if attendees:
            args += ["--attendees", attendees]
        return _run(*args)

    # ── Tasks ────────────────────────────────────────────────────────────────────

    @mcp.tool()
    def feishu_create_task(
        title: str,
        description: str = "",
        due_date: str = "",
        assignee: str = "",
    ) -> dict[str, Any]:
        """Create a task in Feishu Tasks.

        Args:
            title: Task title.
            description: Task description (optional).
            due_date: Due date in ISO 8601 format (optional).
            assignee: Assignee open_id or email (optional).
        """
        args = ["task", "tasks", "create", "--title", title]
        if description:
            args += ["--description", description]
        if due_date:
            args += ["--due-date", due_date]
        if assignee:
            args += ["--assignee", assignee]
        return _run(*args)

    @mcp.tool()
    def feishu_list_tasks(status: str = "todo") -> dict[str, Any]:
        """List Feishu tasks.

        Args:
            status: Filter by status: ``todo``, ``done``, or ``all``.
        """
        return _run("task", "tasks", "list", "--status", status)

    # ── Generic escape hatch ─────────────────────────────────────────────────────

    @mcp.tool()
    def feishu_run_command(command: str) -> dict[str, Any]:
        """Run any lark-cli command and return its output.

        Use this for Feishu operations not covered by the named tools above.
        The command is the portion after ``lark-cli``, e.g. ``"sheets spreadsheets get --spreadsheet-token abc"``.

        Args:
            command: Space-separated lark-cli sub-command and arguments.
        """
        import shlex

        parts = shlex.split(command)
        return _run(*parts, timeout=60)

    return mcp
