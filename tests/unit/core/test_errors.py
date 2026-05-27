"""Tests for the cloud-neutral exception hierarchy."""

from cloud_relay.core.errors import (
    AccessDeniedError,
    CloudRelayError,
    ConflictError,
    ResourceNotFoundError,
    ThrottledError,
    UpstreamError,
    ValidationError,
)


def test_all_subclasses_share_base() -> None:
    for cls in (
        ResourceNotFoundError,
        AccessDeniedError,
        ConflictError,
        ThrottledError,
        ValidationError,
        UpstreamError,
    ):
        assert issubclass(cls, CloudRelayError)
