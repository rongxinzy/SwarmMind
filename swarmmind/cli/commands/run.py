"""Run commands."""

from __future__ import annotations

from typing import Annotated

import typer

from swarmmind.cli.commands._common import run_client_command

run_app = typer.Typer(help="Manage execution runs.", no_args_is_help=True)


@run_app.command("list")
def list_runs(
    ctx: typer.Context,
    project_id: Annotated[str | None, typer.Option("--project-id", help="List project runs.")] = None,
    conversation_id: Annotated[str | None, typer.Option("--conversation-id", help="List conversation runs.")] = None,
) -> None:
    if bool(project_id) == bool(conversation_id):
        raise typer.BadParameter("provide exactly one of --project-id or --conversation-id")
    run_client_command(ctx, lambda client: client.list_runs(project_id=project_id, conversation_id=conversation_id))


@run_app.command("get")
def get_run(
    ctx: typer.Context,
    run_id: Annotated[str, typer.Argument(help="Run ID.")],
) -> None:
    run_client_command(ctx, lambda client: client.get_run(run_id))


@run_app.command("create")
def create_run(
    ctx: typer.Context,
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
    conversation_id: Annotated[str | None, typer.Option("--conversation-id")] = None,
    goal: Annotated[str | None, typer.Option("--goal")] = None,
    status: Annotated[str, typer.Option("--status")] = "running",
) -> None:
    run_client_command(
        ctx,
        lambda client: client.create_run(
            project_id=project_id,
            conversation_id=conversation_id,
            goal=goal,
            status=status,
        ),
    )


@run_app.command("update")
def update_run(
    ctx: typer.Context,
    run_id: Annotated[str, typer.Argument(help="Run ID.")],
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
    status: Annotated[str | None, typer.Option("--status")] = None,
    goal: Annotated[str | None, typer.Option("--goal")] = None,
    summary: Annotated[str | None, typer.Option("--summary")] = None,
) -> None:
    run_client_command(
        ctx,
        lambda client: client.update_run(run_id, project_id=project_id, status=status, goal=goal, summary=summary),
    )
