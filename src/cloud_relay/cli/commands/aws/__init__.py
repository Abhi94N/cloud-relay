"""``cloud-relay aws ...`` Typer sub-application.

Mounts one sub-app per AWS service. When a new cloud joins, create a parallel
``cli/commands/<cloud>/__init__.py`` and mount it on the root app in
:mod:`cloud_relay.cli.main`.
"""

import typer

from cloud_relay.cli.commands.aws import s3, secrets_manager

app = typer.Typer(help="AWS service operations", no_args_is_help=True)
app.add_typer(secrets_manager.app, name="secrets-manager")
app.add_typer(s3.app, name="s3")
