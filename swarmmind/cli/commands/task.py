"""Task commands."""

from __future__ import annotations

from typing import Annotated

import typer

from swarmmind.cli.commands._common import run_client_command, split_csv

task_app = typer.Typer(help="Manage project tasks.", no_args_is_help=True)


@task_app.command("list")
def list_tasks(
    ctx: typer.Context,
    project_id: Annotated[str, typer.Argument(help="Project ID.")],
) -> None:
    run_client_command(ctx, lambda client: client.list_tasks(project_id))


@task_app.command("create")
def create_task(
    ctx: typer.Context,
    project_id: Annotated[str, typer.Argument(help="Project ID.")],
    title: Annotated[str, typer.Argument(help="Task title.")],
    description: Annotated[str | None, typer.Option("--description")] = None,
    status: Annotated[str, typer.Option("--status")] = "todo",
    assignee_role: Annotated[str | None, typer.Option("--assignee-role")] = None,
    source_workstream: Annotated[str | None, typer.Option("--source-workstream")] = None,
    artifact_ids: Annotated[str | None, typer.Option("--artifact-ids", help="Comma-separated artifact IDs.")] = None,
    priority: Annotated[str, typer.Option("--priority")] = "medium",
) -> None:
    run_client_command(
        ctx,
        lambda client: client.create_task(
            project_id,
            title=title,
            description=description,
            status=status,
            assignee_role=assignee_role,
            source_workstream=source_workstream,
            artifact_ids=split_csv(artifact_ids),
            priority=priority,
        ),
    )


@task_app.command("get")
def get_task(
    ctx: typer.Context,
    project_id: Annotated[str, typer.Argument(help="Project ID.")],
    task_id: Annotated[str, typer.Argument(help="Task ID.")],
) -> None:
    run_client_command(ctx, lambda client: client.get_task(project_id, task_id))


@task_app.command("update")
def update_task(
    ctx: typer.Context,
    project_id: Annotated[str, typer.Argument(help="Project ID.")],
    task_id: Annotated[str, typer.Argument(help="Task ID.")],
    title: Annotated[str | None, typer.Option("--title")] = None,
    description: Annotated[str | None, typer.Option("--description")] = None,
    status: Annotated[str | None, typer.Option("--status")] = None,
    assignee_role: Annotated[str | None, typer.Option("--assignee-role")] = None,
    source_workstream: Annotated[str | None, typer.Option("--source-workstream")] = None,
    artifact_ids: Annotated[str | None, typer.Option("--artifact-ids", help="Comma-separated artifact IDs.")] = None,
    priority: Annotated[str | None, typer.Option("--priority")] = None,
) -> None:
    run_client_command(
        ctx,
        lambda client: client.update_task(
            project_id,
            task_id,
            title=title,
            description=description,
            status=status,
            assignee_role=assignee_role,
            source_workstream=source_workstream,
            artifact_ids=split_csv(artifact_ids),
            priority=priority,
        ),
    )


@task_app.command("delete")
def delete_task(
    ctx: typer.Context,
    project_id: Annotated[str, typer.Argument(help="Project ID.")],
    task_id: Annotated[str, typer.Argument(help="Task ID.")],
) -> None:
    run_client_command(ctx, lambda client: client.delete_task(project_id, task_id))
