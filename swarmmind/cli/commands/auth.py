"""Authentication CLI commands."""

from __future__ import annotations

from typing import Annotated

import typer

from swarmmind.cli.commands._common import run_client_command

auth_app = typer.Typer(help="Authenticate against the supervisor API.", no_args_is_help=True)


@auth_app.command("login")
def login(
    ctx: typer.Context,
    username_or_email: Annotated[str, typer.Argument(help="Username or email.")],
    password: Annotated[str, typer.Option("--password", "-p", prompt=True, hide_input=True, help="User password.")],
    token_name: Annotated[str | None, typer.Option("--token-name", help="Human label for this API token.")] = None,
) -> None:
    """Exchange username/email and password for a bearer token."""
    run_client_command(ctx, lambda client: client.login(username_or_email, password, token_name=token_name))


@auth_app.command("me")
def me(ctx: typer.Context) -> None:
    """Show the current authenticated user."""
    run_client_command(ctx, lambda client: client.me())


@auth_app.command("logout")
def logout(ctx: typer.Context) -> None:
    """Revoke the current bearer token."""
    run_client_command(ctx, lambda client: client.logout())
