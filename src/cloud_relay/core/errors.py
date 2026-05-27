"""Cloud-neutral domain exception hierarchy.

These exceptions describe outcomes that any cloud provider can produce
(a missing resource, a permission denial, a throttled request, ...). They are
deliberately decoupled from any specific SDK; provider packages catch their
own SDK errors and translate them into these types -- see
:func:`cloud_relay.services.aws._core.errors.translate_error` for the AWS
implementation.

Adapters (API and CLI) catch these domain types: the API maps them to HTTP
status codes, and the CLI renders them as clean messages with non-zero exit
codes.
"""


class CloudRelayError(Exception):
    """Base class for all cloud-relay domain errors."""


class ResourceNotFoundError(CloudRelayError):
    """The requested cloud resource does not exist."""


class AccessDeniedError(CloudRelayError):
    """The caller lacks permission for the requested operation."""


class ConflictError(CloudRelayError):
    """The resource already exists or is in a conflicting state."""


class ThrottledError(CloudRelayError):
    """The provider throttled the request; a retry may succeed later."""


class ValidationError(CloudRelayError):
    """The request parameters were rejected as invalid by the provider."""


class UpstreamError(CloudRelayError):
    """An unclassified provider-side error. Wraps the original message."""
