"""Secrets Manager specific exceptions.

Most error cases are handled by the shared translation in
:mod:`cloud_relay.services.aws._core.errors`. Define service-specific subclasses
here only where they add clarity for callers.
"""

from cloud_relay.core.errors import ResourceNotFoundError


class SecretNotFoundError(ResourceNotFoundError):
    """The named secret does not exist."""
