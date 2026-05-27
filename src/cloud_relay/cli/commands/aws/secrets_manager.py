"""CLI commands for AWS Secrets Manager.

Each command constructs the service from the shared
:class:`~cloud_relay.cli.context.CliContext`, calls a single service method, and
renders the result via :func:`cloud_relay.cli.output.render`.
"""

from typing import TYPE_CHECKING

import typer
from pydantic import SecretStr

from cloud_relay.cli.output import render
from cloud_relay.services.aws.secrets_manager import (
    CreateSecretRequest,
    DeleteSecretRequest,
    GetSecretValueRequest,
    ListSecretsRequest,
    PutSecretValueRequest,
    SecretsManagerService,
)

if TYPE_CHECKING:
    from cloud_relay.cli.context import CliContext

app = typer.Typer(help="Secrets Manager operations", no_args_is_help=True)


@app.command("get-value")
def get_value(
    ctx: typer.Context,
    secret_id: str = typer.Argument(..., help="Secret name or ARN"),
    version_id: str = typer.Option(None, "--version-id", help="Specific version"),
    show_secret: bool = typer.Option(
        False, "--show-secret", help="Reveal the secret value in output"
    ),
) -> None:
    """Fetch and print a secret's value (masked unless --show-secret)."""
    c: CliContext = ctx.obj
    svc = SecretsManagerService(c.aws_factory)
    result = svc.get_secret_value(
        GetSecretValueRequest(secret_id=secret_id, version_id=version_id)
    )
    typer.echo(render(result, c.output, show_secret=show_secret))


@app.command("create")
def create(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Secret name"),
    value: str = typer.Option(..., "--value", help="Secret string value"),
    description: str = typer.Option(None, "--description"),
) -> None:
    """Create a new secret with a string value."""
    c: CliContext = ctx.obj
    svc = SecretsManagerService(c.aws_factory)
    result = svc.create_secret(
        CreateSecretRequest(
            name=name, secret_string=SecretStr(value), description=description
        )
    )
    typer.echo(render(result, c.output))


@app.command("put-value")
def put_value(
    ctx: typer.Context,
    secret_id: str = typer.Argument(..., help="Secret name or ARN"),
    value: str = typer.Option(..., "--value", help="New secret string value"),
) -> None:
    """Store a new version of an existing secret's value."""
    c: CliContext = ctx.obj
    svc = SecretsManagerService(c.aws_factory)
    result = svc.put_secret_value(
        PutSecretValueRequest(secret_id=secret_id, secret_string=SecretStr(value))
    )
    typer.echo(render(result, c.output))


@app.command("describe")
def describe(
    ctx: typer.Context,
    secret_id: str = typer.Argument(..., help="Secret name or ARN"),
) -> None:
    """Print a secret's metadata (no value)."""
    c: CliContext = ctx.obj
    svc = SecretsManagerService(c.aws_factory)
    result = svc.describe_secret(secret_id)
    typer.echo(render(result, c.output))


@app.command("list")
def list_secrets(
    ctx: typer.Context,
    name_prefix: str = typer.Option(None, "--prefix", help="Filter by name prefix"),
    max_results: int = typer.Option(None, "--max", help="Cap on results"),
) -> None:
    """List secrets, optionally filtered by name prefix."""
    c: CliContext = ctx.obj
    svc = SecretsManagerService(c.aws_factory)
    results = svc.list_secrets(
        ListSecretsRequest(name_prefix=name_prefix, max_results=max_results)
    )
    typer.echo(render(results, c.output))


@app.command("delete")
def delete(
    ctx: typer.Context,
    secret_id: str = typer.Argument(..., help="Secret name or ARN"),
    force: bool = typer.Option(False, "--force", help="Delete without recovery"),
    recovery_window_days: int = typer.Option(
        None, "--recovery-days", help="Recovery window (7-30)"
    ),
) -> None:
    """Delete a secret, optionally forcing immediate deletion."""
    c: CliContext = ctx.obj
    svc = SecretsManagerService(c.aws_factory)
    result = svc.delete_secret(
        DeleteSecretRequest(
            secret_id=secret_id,
            force_delete=force,
            recovery_window_days=recovery_window_days,
        )
    )
    typer.echo(render(result, c.output))
