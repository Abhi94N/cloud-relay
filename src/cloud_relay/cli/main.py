"""cloud-relay CLI entry point.

Defines the root Typer application, mounts one sub-app per cloud provider,
builds the shared :class:`~cloud_relay.cli.context.CliContext` from global
options, and renders domain errors as clean messages with non-zero exit codes
(no traceback).
"""

import typer

from cloud_relay.cli.commands import aws
from cloud_relay.cli.context import CliContext
from cloud_relay.core.config import get_settings
from cloud_relay.core.errors import CloudRelayError
from cloud_relay.core.logging import configure_logging
from cloud_relay.services.aws._core import AwsSettings, ClientFactory

app = typer.Typer(
    name="cloud-relay",
    help="Consolidated cloud service wrappers (library + CLI + API).",
    no_args_is_help=True,
)
app.add_typer(aws.app, name="aws")


@app.callback()
def main(
    ctx: typer.Context,
    output: str = typer.Option("json", "--output", "-o", help="json|table|yaml"),
    region: str = typer.Option(None, "--region", help="AWS region override"),
    profile: str = typer.Option(None, "--profile", help="AWS profile"),
) -> None:
    """Build the shared CLI context from global options.

    Cloud-neutral logging is configured once, here. CLI overrides
    (``--region`` / ``--profile``) are passed through ``AwsSettings``
    construction so Pydantic validators run; we never mutate a built model.
    """
    settings = get_settings()
    configure_logging(settings)

    # AwsSettings reads env (CLOUD_RELAY_*, AWS_*). Constructor args, when
    # provided, take precedence; passing None defers to env, which is what we
    # want when the user did not pass --region/--profile.
    aws_kwargs: dict[str, object] = {}
    if region:
        aws_kwargs["region"] = region
    if profile:
        aws_kwargs["profile"] = profile
    aws_settings = AwsSettings(**aws_kwargs)  # type: ignore[arg-type]

    ctx.obj = CliContext(
        settings=settings,
        aws_factory=ClientFactory(aws_settings),
        output=output,
    )


def run() -> None:
    """Console-script entry point.

    Wraps the Typer app so domain errors surface as clean, colored messages
    with a non-zero exit code instead of a Python traceback.
    """
    try:
        app()
    except CloudRelayError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    run()
