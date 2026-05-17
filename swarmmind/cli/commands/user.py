"""User management CLI commands."""

from __future__ import annotations

from typing import Annotated

import typer

from swarmmind.cli.commands._common import run_client_command

user_app = typer.Typer(help="Manage local users.", no_args_is_help=True)


@user_app.command("list")
def list_users(ctx: typer.Context) -> None:
    """List local users."""
    run_client_command(ctx, lambda client: client.list_users())


@user_app.command("create")
def create_user(
    ctx: typer.Context,
    email: Annotated[str, typer.Argument(help="User email.")],
    password: Annotated[str, typer.Option("--password", "-p", prompt=True, hide_input=True, help="Initial password.")],
    display_name: Annotated[str | None, typer.Option("--display-name", help="Display name.")] = None,
    role: Annotated[str, typer.Option("--role", help="User role: admin or member.")] = "member",
) -> None:
    """Create a local user."""
    run_client_command(
        ctx,
        lambda client: client.create_user(email=email, password=password, display_name=display_name, role=role),
    )


@user_app.command("get")
def get_user(
    ctx: typer.Context,
    user_id: Annotated[str, typer.Argument(help="User ID.")],
) -> None:
    """Get a local user."""
    run_client_command(ctx, lambda client: client.get_user(user_id))


@user_app.command("update")
def update_user(
    ctx: typer.Context,
    user_id: Annotated[str, typer.Argument(help="User ID.")],
    email: Annotated[str | None, typer.Option("--email", help="New email.")] = None,
    password: Annotated[str | None, typer.Option("--password", "-p", help="New password.")] = None,
    display_name: Annotated[str | None, typer.Option("--display-name", help="Display name.")] = None,
    role: Annotated[str | None, typer.Option("--role", help="User role: admin or member.")] = None,
    status: Annotated[str | None, typer.Option("--status", help="User status: active or disabled.")] = None,
) -> None:
    """Update a local user."""
    run_client_command(
        ctx,
        lambda client: client.update_user(
            user_id,
            email=email,
            password=password,
            display_name=display_name,
            role=role,
            status=status,
        ),
    )


@user_app.command("disable")
def disable_user(
    ctx: typer.Context,
    user_id: Annotated[str, typer.Argument(help="User ID.")],
) -> None:
    """Disable a local user and revoke its tokens."""
    run_client_command(ctx, lambda client: client.delete_user(user_id))
