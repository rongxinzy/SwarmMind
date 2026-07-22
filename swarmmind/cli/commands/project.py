"""Project commands."""

from __future__ import annotations

from typing import Annotated

import typer

from swarmmind.cli.commands._common import run_client_command

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
    next_step: Annotated[str | None, typer.Option("--next-step")] = None,
    phase: Annotated[str | None, typer.Option("--phase")] = None,
    risk_level: Annotated[str | None, typer.Option("--risk-level")] = None,
) -> None:
    run_client_command(
        ctx,
        lambda client: client.create_project(
            title=title,
            goal=goal,
            scope=scope,
            constraints=constraints,
            next_step=next_step,
            phase=phase,
            risk_level=risk_level,
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


@project_app.command("delete")
def delete_project(
    ctx: typer.Context,
    project_id: Annotated[str, typer.Argument(help="Project ID.")],
) -> None:
    run_client_command(ctx, lambda client: client.delete_project(project_id))
