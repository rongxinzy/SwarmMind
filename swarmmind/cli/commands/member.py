"""Project membership commands."""

from __future__ import annotations

from typing import Annotated

import typer

from swarmmind.cli.commands._common import run_client_command

member_app = typer.Typer(help="Manage project memberships and minimal RBAC.", no_args_is_help=True)


@member_app.command("list")
def list_members(
    ctx: typer.Context,
    project_id: Annotated[str, typer.Argument(help="Project ID.")],
) -> None:
    run_client_command(ctx, lambda client: client.list_project_members(project_id))


@member_app.command("add")
def add_member(
    ctx: typer.Context,
    project_id: Annotated[str, typer.Argument(help="Project ID.")],
    member_id: Annotated[str, typer.Argument(help="User/service principal ID.")],
    role: Annotated[str, typer.Option("--role", help="owner, editor, approver, or viewer.")] = "viewer",
    display_name: Annotated[str | None, typer.Option("--display-name")] = None,
    status: Annotated[str, typer.Option("--status", help="active or inactive.")] = "active",
) -> None:
    run_client_command(
        ctx,
        lambda client: client.create_project_member(
            project_id,
            member_id=member_id,
            display_name=display_name,
            role=role,
            status=status,
        ),
    )


@member_app.command("get")
def get_member(
    ctx: typer.Context,
    project_id: Annotated[str, typer.Argument(help="Project ID.")],
    member_id: Annotated[str, typer.Argument(help="User/service principal ID.")],
) -> None:
    run_client_command(ctx, lambda client: client.get_project_member(project_id, member_id))


@member_app.command("update")
def update_member(
    ctx: typer.Context,
    project_id: Annotated[str, typer.Argument(help="Project ID.")],
    member_id: Annotated[str, typer.Argument(help="User/service principal ID.")],
    role: Annotated[str | None, typer.Option("--role", help="owner, editor, approver, or viewer.")] = None,
    display_name: Annotated[str | None, typer.Option("--display-name")] = None,
    status: Annotated[str | None, typer.Option("--status", help="active or inactive.")] = None,
) -> None:
    run_client_command(
        ctx,
        lambda client: client.update_project_member(
            project_id,
            member_id,
            role=role,
            display_name=display_name,
            status=status,
        ),
    )


@member_app.command("remove")
def remove_member(
    ctx: typer.Context,
    project_id: Annotated[str, typer.Argument(help="Project ID.")],
    member_id: Annotated[str, typer.Argument(help="User/service principal ID.")],
) -> None:
    run_client_command(ctx, lambda client: client.delete_project_member(project_id, member_id))


@member_app.command("can")
def check_member_permission(
    ctx: typer.Context,
    project_id: Annotated[str, typer.Argument(help="Project ID.")],
    member_id: Annotated[str, typer.Argument(help="User/service principal ID.")],
    capability: Annotated[
        str,
        typer.Argument(help="view_project, run_project, manage_project, approve_high_risk, or manage_members."),
    ],
) -> None:
    run_client_command(ctx, lambda client: client.check_project_permission(project_id, member_id, capability))
