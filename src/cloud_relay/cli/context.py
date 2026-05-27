"""Shared CLI context object.

A single :class:`CliContext` is built once in the root Typer callback and
attached to ``ctx.obj``; every command reads its settings, AWS client factory,
and chosen output format from it.

When a new cloud is added, give :class:`CliContext` an additional optional
factory field (e.g. ``gcp_factory: GcpClientFactory | None``) so commands for
that cloud can pick it up. AWS-only commands continue to read ``aws_factory``.
"""

from dataclasses import dataclass

from cloud_relay.core.config import Settings
from cloud_relay.services.aws._core import ClientFactory as AwsClientFactory


@dataclass
class CliContext:
    """Carries resolved configuration through to each command.

    Attributes:
        settings: The cloud-neutral :class:`Settings` for this invocation.
        aws_factory: The AWS client factory commands use to construct services.
        output: The chosen output format: ``"json"``, ``"table"``, or ``"yaml"``.
    """

    settings: Settings
    aws_factory: AwsClientFactory
    output: str
