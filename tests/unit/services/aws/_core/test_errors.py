"""Tests for botocore -> domain error translation."""

from botocore.exceptions import ClientError

from cloud_relay.core.errors import (
    AccessDeniedError,
    ResourceNotFoundError,
    UpstreamError,
)
from cloud_relay.services.aws._core import translate_error


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "boom"}}, "Op")


def test_known_codes_map() -> None:
    assert isinstance(
        translate_error(_client_error("ResourceNotFoundException")),
        ResourceNotFoundError,
    )
    assert isinstance(
        translate_error(_client_error("AccessDeniedException")), AccessDeniedError
    )


def test_unknown_code_falls_back_to_upstream() -> None:
    assert isinstance(translate_error(_client_error("WeirdNewError")), UpstreamError)


def test_message_preserved() -> None:
    assert "boom" in str(translate_error(_client_error("AccessDenied")))
