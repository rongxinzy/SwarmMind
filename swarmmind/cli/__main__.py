"""SwarmMind command-line entrypoint."""

from __future__ import annotations

from importlib import metadata
from typing import Annotated

import typer

from swarmmind import __version__
from swarmmind.cli.commands.approval import approval_app
from swarmmind.cli.commands.audit import audit_app
from swarmmind.cli.commands.conversation import chat_app, conversation_app
from swarmmind.cli.commands.mcp import mcp_app
from swarmmind.cli.commands.memory import memory_app
from swarmmind.cli.commands.project import project_app
from swarmmind.cli.commands.run import run_app
from swarmmind.cli.commands.system import register_system_commands
from swarmmind.cli.commands.task import task_app
from swarmmind.cli.config import CLIState, resolve_api_url

app = typer.Typer(
    help="SwarmMind CLI: HTTP-first client for the supervisor API.",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)


def _version_callback(value: bool) -> bool:
    if value:
        typer.echo(f"swarmmind {_version()}")
        raise typer.Exit()
    return value


@app.callback()
def main(
    ctx: typer.Context,
    api_url: Annotated[str | None, typer.Option("--api-url", help="Supervisor API URL.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON or NDJSON output.")] = False,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress normal output.")] = False,
    version: Annotated[
        bool,
        typer.Option("--version", help="Show CLI version and exit.", callback=_version_callback, is_eager=True),
    ] = False,
) -> None:
    """Resolve global CLI options."""
    _ = version
    ctx.obj = CLIState(api_url=resolve_api_url(api_url), json_output=json_output, quiet=quiet)


def _version() -> str:
    try:
        return metadata.version("swarmmind")
    except metadata.PackageNotFoundError:
        return __version__


register_system_commands(app)
app.add_typer(conversation_app, name="conversation")
app.add_typer(chat_app, name="chat")
app.add_typer(project_app, name="project")
app.add_typer(run_app, name="run")
app.add_typer(task_app, name="task")
app.add_typer(approval_app, name="approval")
app.add_typer(audit_app, name="audit")
app.add_typer(memory_app, name="memory")
app.add_typer(mcp_app, name="mcp")


if __name__ == "__main__":
    app()
