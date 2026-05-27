"""CLI commands for AWS S3 (scaffold).

``head-object`` is implemented as a worked example; other commands are stubs
that exit non-zero until implemented. See ``services/aws/s3/EXTENDING.md``.
"""

from typing import TYPE_CHECKING

import typer

from cloud_relay.cli.output import render
from cloud_relay.services.aws.s3 import HeadObjectRequest, S3Service

if TYPE_CHECKING:
    from cloud_relay.cli.context import CliContext

app = typer.Typer(help="S3 operations", no_args_is_help=True)


@app.command("head-object")
def head_object(
    ctx: typer.Context,
    bucket: str = typer.Argument(..., help="Bucket name"),
    key: str = typer.Argument(..., help="Object key"),
    version_id: str = typer.Option(None, "--version-id"),
) -> None:
    """Print object metadata without downloading the body."""
    c: CliContext = ctx.obj
    svc = S3Service(c.aws_factory)
    result = svc.head_object(
        HeadObjectRequest(bucket=bucket, key=key, version_id=version_id)
    )
    typer.echo(render(result, c.output))


@app.command("list-objects")
def list_objects(ctx: typer.Context) -> None:
    """List objects in a bucket. Not yet implemented (see EXTENDING.md)."""
    typer.secho(
        "s3 list-objects is not implemented yet -- see services/aws/s3/EXTENDING.md",
        fg=typer.colors.YELLOW,
    )
    raise typer.Exit(1)
