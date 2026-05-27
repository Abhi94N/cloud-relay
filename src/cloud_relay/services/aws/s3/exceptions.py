"""S3-specific exceptions.

Most cases are covered by :mod:`cloud_relay.services.aws._core.errors`. Add
subclasses here only where they add clarity.
"""

from cloud_relay.core.errors import ResourceNotFoundError


class ObjectNotFoundError(ResourceNotFoundError):
    """The requested S3 object or bucket does not exist."""
