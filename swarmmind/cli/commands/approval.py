"""Approval commands."""

from __future__ import annotations

from typing import Annotated

import typer

from swarmmind.cli.commands._common import run_client_command

approval_app = typer.Typer(help="Manage approval requests.", no_args_is_help=True)


@approval_app.command("list")
def list_approvals(
    ctx: typer.Context,
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
    status: Annotated[str | None, typer.Option("--status")] = None,
    risk_tier: Annotated[str | None, typer.Option("--risk-tier")] = None,
) -> None:
    run_client_command(
        ctx,
        lambda client: client.list_approvals(project_id=project_id, status=status, risk_tier=risk_tier),
    )


@approval_app.command("create")
def create_approval(
    ctx: typer.Context,
    project_id: Annotated[str, typer.Argument(help="Project ID.")],
    title: Annotated[str, typer.Argument(help="Approval title.")],
    run_id: Annotated[str | None, typer.Option("--run-id")] = None,
    description: Annotated[str | None, typer.Option("--description")] = None,
    risk_tier: Annotated[str, typer.Option("--risk-tier")] = "medium",
    requested_capability: Annotated[str | None, typer.Option("--requested-capability")] = None,
    evidence: Annotated[str | None, typer.Option("--evidence")] = None,
    impact: Annotated[str | None, typer.Option("--impact")] = None,
    approver_role: Annotated[str | None, typer.Option("--approver-role")] = None,
    recovery_behavior: Annotated[str | None, typer.Option("--recovery-behavior")] = None,
) -> None:
    run_client_command(
        ctx,
        lambda client: client.create_approval(
            project_id=project_id,
            run_id=run_id,
            title=title,
            description=description,
            risk_tier=risk_tier,
            requested_capability=requested_capability,
            evidence=evidence,
            impact=impact,
            approver_role=approver_role,
            recovery_behavior=recovery_behavior,
        ),
    )


@approval_app.command("get")
def get_approval(
    ctx: typer.Context,
    approval_id: Annotated[str, typer.Argument(help="Approval ID.")],
) -> None:
    run_client_command(ctx, lambda client: client.get_approval(approval_id))


@approval_app.command("update")
def update_approval(
    ctx: typer.Context,
    approval_id: Annotated[str, typer.Argument(help="Approval ID.")],
    status: Annotated[str | None, typer.Option("--status")] = None,
    decision_reason: Annotated[str | None, typer.Option("--decision-reason")] = None,
    title: Annotated[str | None, typer.Option("--title")] = None,
    description: Annotated[str | None, typer.Option("--description")] = None,
    risk_tier: Annotated[str | None, typer.Option("--risk-tier")] = None,
) -> None:
    run_client_command(
        ctx,
        lambda client: client.update_approval(
            approval_id,
            status=status,
            decision_reason=decision_reason,
            title=title,
            description=description,
            risk_tier=risk_tier,
        ),
    )


@approval_app.command("delete")
def delete_approval(
    ctx: typer.Context,
    approval_id: Annotated[str, typer.Argument(help="Approval ID.")],
) -> None:
    run_client_command(ctx, lambda client: client.delete_approval(approval_id))
