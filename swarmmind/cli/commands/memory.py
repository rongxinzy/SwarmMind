"""Layered memory commands."""

from __future__ import annotations

from typing import Annotated

import typer

from swarmmind.cli.commands._common import run_client_command

memory_app = typer.Typer(help="Read layered memory entries.", no_args_is_help=True)


@memory_app.command("list")
def list_memory(
    ctx: typer.Context,
    layer: Annotated[str | None, typer.Option("--layer", help="Memory layer, e.g. L3_project.")] = None,
    scope_id: Annotated[str | None, typer.Option("--scope-id", help="Scope ID within the layer.")] = None,
    tag: Annotated[list[str] | None, typer.Option("--tag", help="Repeatable tag filter.")] = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=500)] = 100,
) -> None:
    run_client_command(ctx, lambda client: client.list_memory(layer=layer, scope_id=scope_id, tags=tag, limit=limit))


@memory_app.command("get")
def get_memory(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument(help="Memory key.")],
    layer: Annotated[str, typer.Option("--layer", help="Memory layer, e.g. L3_project.")],
    scope_id: Annotated[str, typer.Option("--scope-id", help="Scope ID within the layer.")],
) -> None:
    run_client_command(ctx, lambda client: client.get_memory(key, layer=layer, scope_id=scope_id))
