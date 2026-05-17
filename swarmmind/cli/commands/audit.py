"""Audit log commands."""

from __future__ import annotations

from typing import Annotated

import typer

from swarmmind.cli.commands._common import run_client_command

audit_app = typer.Typer(help="Read and write audit logs.", no_args_is_help=True)


@audit_app.command("list")
def list_audit_logs(
    ctx: typer.Context,
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
    run_id: Annotated[str | None, typer.Option("--run-id")] = None,
    approval_id: Annotated[str | None, typer.Option("--approval-id")] = None,
) -> None:
    run_client_command(
        ctx,
        lambda client: client.list_audit_logs(project_id=project_id, run_id=run_id, approval_id=approval_id),
    )


@audit_app.command("get")
def get_audit_log(
    ctx: typer.Context,
    audit_id: Annotated[str, typer.Argument(help="Audit log ID.")],
) -> None:
    run_client_command(ctx, lambda client: client.get_audit_log(audit_id))


@audit_app.command("create")
def create_audit_log(
    ctx: typer.Context,
    project_id: Annotated[str, typer.Argument(help="Project ID.")],
    audit_type: Annotated[str, typer.Option("--audit-type")] = "approval_decision",
    run_id: Annotated[str | None, typer.Option("--run-id")] = None,
    approval_id: Annotated[str | None, typer.Option("--approval-id")] = None,
    actor_id: Annotated[str | None, typer.Option("--actor-id")] = None,
    actor_type: Annotated[str, typer.Option("--actor-type")] = "user",
    decision: Annotated[str | None, typer.Option("--decision")] = None,
    reason: Annotated[str | None, typer.Option("--reason")] = None,
) -> None:
    run_client_command(
        ctx,
        lambda client: client.create_audit_log(
            project_id=project_id,
            audit_type=audit_type,
            run_id=run_id,
            approval_id=approval_id,
            actor_id=actor_id,
            actor_type=actor_type,
            decision=decision,
            reason=reason,
        ),
    )


@audit_app.command("delete")
def delete_audit_log(
    ctx: typer.Context,
    audit_id: Annotated[str, typer.Argument(help="Audit log ID.")],
) -> None:
    run_client_command(ctx, lambda client: client.delete_audit_log(audit_id))
