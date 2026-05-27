"""boto3 -> domain exception translation for AWS.

AWS services catch botocore's :class:`~botocore.exceptions.ClientError` and
convert it into one of the cloud-neutral domain exceptions defined in
:mod:`cloud_relay.core.errors` via :func:`translate_error`. Adapters then catch
the domain types and never see boto3 directly.

When a new cloud is added, give it its own translator (e.g.
``services/gcp/_core/errors.py`` mapping ``google.api_core`` exceptions onto
the same :class:`~cloud_relay.core.errors.CloudRelayError` hierarchy).
"""

from botocore.exceptions import ClientError

from cloud_relay.core.errors import (
    AccessDeniedError,
    CloudRelayError,
    ConflictError,
    ResourceNotFoundError,
    ThrottledError,
    UpstreamError,
    ValidationError,
)

# Maps botocore error codes to cloud-neutral domain exceptions.
_ERROR_CODE_MAP: dict[str, type[CloudRelayError]] = {
    "ResourceNotFoundException": ResourceNotFoundError,
    "NoSuchKey": ResourceNotFoundError,
    "NoSuchBucket": ResourceNotFoundError,
    "404": ResourceNotFoundError,
    "AccessDeniedException": AccessDeniedError,
    "AccessDenied": AccessDeniedError,
    "ResourceExistsException": ConflictError,
    "BucketAlreadyExists": ConflictError,
    "BucketAlreadyOwnedByYou": ConflictError,
    "ThrottlingException": ThrottledError,
    "Throttling": ThrottledError,
    "TooManyRequestsException": ThrottledError,
    "ValidationException": ValidationError,
    "InvalidParameterException": ValidationError,
    "InvalidRequestException": ValidationError,
}


def translate_error(exc: ClientError) -> CloudRelayError:
    """Convert a botocore :class:`ClientError` into a domain exception.

    The botocore error *code* is mapped to a domain exception type; unknown
    codes fall back to :class:`UpstreamError`. Always chain the original::

        try:
            self._client.some_call(...)
        except ClientError as e:
            raise translate_error(e) from e

    Args:
        exc: The botocore error raised by a boto3 call.

    Returns:
        The corresponding domain exception, carrying the AWS error message.
    """
    err = exc.response.get("Error", {})
    cls = _ERROR_CODE_MAP.get(err.get("Code", ""), UpstreamError)
    return cls(err.get("Message", str(exc)))
