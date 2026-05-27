"""Tests for the AWS client factory."""

from cloud_relay.services.aws._core import ClientFactory


def test_client_is_cached(factory: ClientFactory) -> None:
    a = factory.client("secretsmanager")
    b = factory.client("secretsmanager")
    assert a is b


def test_different_services_distinct(factory: ClientFactory) -> None:
    assert factory.client("s3") is not factory.client("secretsmanager")
