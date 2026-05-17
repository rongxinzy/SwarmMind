"""Conversation and chat commands."""

from __future__ import annotations

import json
from typing import Annotated

import typer
from pydantic import ValidationError

from swarmmind.cli.client import ParameterError, SwarmMindCLIError
from swarmmind.cli.commands._common import joined_message, run_client_command, run_stream_command
from swarmmind.cli.config import get_client, get_state
from swarmmind.cli.output import render_error, render_result, render_stream_event

conversation_app = typer.Typer(help="Manage ChatSession records.", no_args_is_help=True)
chat_app = typer.Typer(help="Send ChatSession messages.", no_args_is_help=True)


@conversation_app.command("list")
def list_conversations(ctx: typer.Context) -> None:
    run_client_command(ctx, lambda client: client.list_conversations())


@conversation_app.command("recent")
def recent_conversation(ctx: typer.Context) -> None:
    run_client_command(ctx, lambda client: client.recent_conversation())


@conversation_app.command("search")
def search_conversations(
    ctx: typer.Context,
    query: Annotated[str, typer.Argument(help="Search query.")],
    limit: Annotated[int, typer.Option("--limit", min=1, max=100)] = 20,
) -> None:
    run_client_command(ctx, lambda client: client.search_conversations(query, limit=limit))


@conversation_app.command("create")
def create_conversation(
    ctx: typer.Context,
    title: Annotated[str | None, typer.Option("--title", "-t", help="Optional conversation title.")] = None,
) -> None:
    run_client_command(ctx, lambda client: client.create_conversation(title=title))


@conversation_app.command("get")
def get_conversation(
    ctx: typer.Context,
    conversation_id: Annotated[str, typer.Argument(help="Conversation ID.")],
    include_messages: Annotated[bool, typer.Option("--include-messages", help="Include messages in response.")] = False,
) -> None:
    run_client_command(ctx, lambda client: client.get_conversation(conversation_id, include_messages=include_messages))


@conversation_app.command("messages")
def list_messages(
    ctx: typer.Context,
    conversation_id: Annotated[str, typer.Argument(help="Conversation ID.")],
) -> None:
    run_client_command(ctx, lambda client: client.list_messages(conversation_id))


@conversation_app.command("trace")
def conversation_trace(
    ctx: typer.Context,
    conversation_id: Annotated[str, typer.Argument(help="Conversation ID.")],
) -> None:
    run_client_command(ctx, lambda client: client.get_conversation_trace(conversation_id))


@conversation_app.command("export")
def export_conversation(
    ctx: typer.Context,
    conversation_id: Annotated[str, typer.Argument(help="Conversation ID.")],
    export_format: Annotated[str, typer.Option("--format", help="markdown or json.")] = "markdown",
) -> None:
    run_client_command(ctx, lambda client: client.export_conversation(conversation_id, export_format=export_format))


@conversation_app.command("delete")
def delete_conversation(
    ctx: typer.Context,
    conversation_id: Annotated[str, typer.Argument(help="Conversation ID.")],
) -> None:
    run_client_command(ctx, lambda client: client.delete_conversation(conversation_id))


@chat_app.command("send")
def send_chat(
    ctx: typer.Context,
    conversation_id: Annotated[str, typer.Argument(help="Conversation ID.")],
    message: Annotated[list[str], typer.Argument(help="Message text.")],
    mode: Annotated[str | None, typer.Option("--mode", help="flash, thinking, pro, or ultra.")] = None,
    model_name: Annotated[str | None, typer.Option("--model", help="Runtime model option name.")] = None,
    reasoning: Annotated[bool, typer.Option("--reasoning", help="Enable legacy reasoning flag.")] = False,
) -> None:
    content = joined_message(message)
    run_client_command(
        ctx,
        lambda client: client.send_message(
            conversation_id, content, mode=mode, model_name=model_name, reasoning=reasoning
        ),
    )


@chat_app.command("stream")
def stream_chat(
    ctx: typer.Context,
    conversation_id: Annotated[str, typer.Argument(help="Conversation ID.")],
    message: Annotated[list[str], typer.Argument(help="Message text.")],
    mode: Annotated[str | None, typer.Option("--mode", help="flash, thinking, pro, or ultra.")] = None,
    model_name: Annotated[str | None, typer.Option("--model", help="Runtime model option name.")] = None,
    reasoning: Annotated[bool, typer.Option("--reasoning", help="Enable legacy reasoning flag.")] = False,
) -> None:
    content = joined_message(message)
    run_stream_command(
        ctx,
        lambda client: client.stream_message(
            conversation_id, content, mode=mode, model_name=model_name, reasoning=reasoning
        ),
    )


@chat_app.command("new")
def new_chat(
    ctx: typer.Context,
    message: Annotated[list[str], typer.Argument(help="First message text.")],
    title: Annotated[str | None, typer.Option("--title", "-t", help="Optional conversation title.")] = None,
    mode: Annotated[str | None, typer.Option("--mode", help="flash, thinking, pro, or ultra.")] = None,
    model_name: Annotated[str | None, typer.Option("--model", help="Runtime model option name.")] = None,
    reasoning: Annotated[bool, typer.Option("--reasoning", help="Enable legacy reasoning flag.")] = False,
) -> None:
    state = get_state(ctx)
    content = joined_message(message)
    try:
        with get_client(ctx) as client:
            conversation = client.create_conversation(title=title)
            conversation_event = {"type": "conversation", "conversation": conversation.model_dump(mode="json")}
            if state.json_output:
                typer.echo(json.dumps(conversation_event, ensure_ascii=False, separators=(",", ":")))
            else:
                render_result(conversation, json_output=False)
            for event in client.stream_message(
                conversation.id, content, mode=mode, model_name=model_name, reasoning=reasoning
            ):
                render_stream_event(event, json_output=state.json_output)
    except ValidationError as exc:
        normalized = ParameterError(str(exc))
        render_error(normalized, json_output=state.json_output, quiet=state.quiet)
        raise typer.Exit(normalized.exit_code) from exc
    except SwarmMindCLIError as exc:
        render_error(exc, json_output=state.json_output, quiet=state.quiet)
        raise typer.Exit(exc.exit_code) from exc


@chat_app.command("respond-clarification")
def respond_clarification(
    ctx: typer.Context,
    conversation_id: Annotated[str, typer.Argument(help="Conversation ID.")],
    tool_call_id: Annotated[str, typer.Argument(help="Clarification tool call ID.")],
    response: Annotated[list[str], typer.Argument(help="Clarification response.")],
) -> None:
    run_client_command(
        ctx,
        lambda client: client.respond_to_clarification(conversation_id, tool_call_id, joined_message(response)),
    )
