"""Tests for the BaseService contract (AWS)."""

import pytest

from cloud_relay.services.aws._core import BaseService


def test_missing_service_name_raises(factory) -> None:
    class NoName(BaseService):
        pass

    with pytest.raises(NotImplementedError):
        NoName(factory)


def test_valid_subclass_resolves_client(factory) -> None:
    class Example(BaseService):
        service_name = "secretsmanager"

    svc = Example(factory)
    assert svc._client is not None
