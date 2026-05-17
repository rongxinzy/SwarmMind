"""Project commands."""

from __future__ import annotations

from typing import Annotated

import typer

from swarmmind.cli.commands._common import joined_message, run_client_command, run_stream_command

project_app = typer.Typer(help="Manage governed projects.", no_args_is_help=True)


@project_app.command("list")
def list_projects(
    ctx: typer.Context,
    limit: Annotated[int | None, typer.Option("--limit", min=1, max=500)] = None,
    offset: Annotated[int, typer.Option("--offset", min=0)] = 0,
) -> None:
    run_client_command(ctx, lambda client: client.list_projects(limit=limit, offset=offset))


@project_app.command("create")
def create_project(
    ctx: typer.Context,
    title: Annotated[str, typer.Argument(help="Project title.")],
    goal: Annotated[str | None, typer.Option("--goal", help="Project goal.")] = None,
    scope: Annotated[str | None, typer.Option("--scope", help="Project scope.")] = None,
    constraints: Annotated[str | None, typer.Option("--constraints", help="Project constraints.")] = None,
    source_conversation_id: Annotated[str | None, typer.Option("--source-conversation-id")] = None,
    next_step: Annotated[str | None, typer.Option("--next-step")] = None,
    phase: Annotated[str | None, typer.Option("--phase")] = None,
    risk_level: Annotated[str | None, typer.Option("--risk-level")] = None,
    team_template_id: Annotated[str | None, typer.Option("--team-template-id")] = None,
) -> None:
    run_client_command(
        ctx,
        lambda client: client.create_project(
            title=title,
            goal=goal,
            scope=scope,
            constraints=constraints,
            source_conversation_id=source_conversation_id,
            next_step=next_step,
            phase=phase,
            risk_level=risk_level,
            team_template_id=team_template_id,
        ),
    )


@project_app.command("get")
def get_project(
    ctx: typer.Context,
    project_id: Annotated[str, typer.Argument(help="Project ID.")],
) -> None:
    run_client_command(ctx, lambda client: client.get_project(project_id))


@project_app.command("update")
def update_project(
    ctx: typer.Context,
    project_id: Annotated[str, typer.Argument(help="Project ID.")],
    title: Annotated[str | None, typer.Option("--title")] = None,
    goal: Annotated[str | None, typer.Option("--goal")] = None,
    scope: Annotated[str | None, typer.Option("--scope")] = None,
    constraints: Annotated[str | None, typer.Option("--constraints")] = None,
    next_step: Annotated[str | None, typer.Option("--next-step")] = None,
    phase: Annotated[str | None, typer.Option("--phase")] = None,
    risk_level: Annotated[str | None, typer.Option("--risk-level")] = None,
    status: Annotated[str | None, typer.Option("--status")] = None,
) -> None:
    run_client_command(
        ctx,
        lambda client: client.update_project(
            project_id,
            title=title,
            goal=goal,
            scope=scope,
            constraints=constraints,
            next_step=next_step,
            phase=phase,
            risk_level=risk_level,
            status=status,
        ),
    )


@project_app.command("overview")
def project_overview(
    ctx: typer.Context,
    project_id: Annotated[str, typer.Argument(help="Project ID.")],
) -> None:
    run_client_command(ctx, lambda client: client.project_overview(project_id))


@project_app.command("delete")
def delete_project(
    ctx: typer.Context,
    project_id: Annotated[str, typer.Argument(help="Project ID.")],
) -> None:
    run_client_command(ctx, lambda client: client.delete_project(project_id))


@project_app.command("stream")
def stream_project(
    ctx: typer.Context,
    project_id: Annotated[str, typer.Argument(help="Project ID.")],
    message: Annotated[list[str], typer.Argument(help="Message text.")],
    mode: Annotated[str | None, typer.Option("--mode", help="flash, thinking, pro, or ultra.")] = None,
    model_name: Annotated[str | None, typer.Option("--model", help="Runtime model option name.")] = None,
    reasoning: Annotated[bool, typer.Option("--reasoning", help="Enable legacy reasoning flag.")] = False,
) -> None:
    content = joined_message(message)
    run_stream_command(
        ctx,
        lambda client: client.stream_project_message(
            project_id, content, mode=mode, model_name=model_name, reasoning=reasoning
        ),
    )
