"""Root-level system commands."""

from __future__ import annotations

from typing import Annotated

import typer

from swarmmind.cli.commands._common import joined_message, run_client_command


def register_system_commands(app: typer.Typer) -> None:
    """Register system and dispatch commands on the root app."""

    @app.command("health")
    def health(ctx: typer.Context) -> None:
        run_client_command(ctx, lambda client: client.health())

    @app.command("ready")
    def ready(ctx: typer.Context) -> None:
        run_client_command(ctx, lambda client: client.ready())

    @app.command("dispatch")
    def dispatch(
        ctx: typer.Context,
        goal: Annotated[list[str], typer.Argument(help="Goal text.")],
    ) -> None:
        run_client_command(ctx, lambda client: client.dispatch(joined_message(goal)))

    @app.command("serve")
    def serve(
        host: Annotated[str, typer.Option("--host", help="API bind host.")] = "127.0.0.1",
        port: Annotated[int, typer.Option("--port", help="API bind port.")] = 8000,
        reload: Annotated[bool, typer.Option("--reload", help="Enable uvicorn reload.")] = False,
    ) -> None:
        import uvicorn

        if reload:
            uvicorn.run("swarmmind.api.supervisor:app", host=host, port=port, reload=True)
            return

        from swarmmind.api.supervisor import app as supervisor_app

        uvicorn.run(supervisor_app, host=host, port=port)
