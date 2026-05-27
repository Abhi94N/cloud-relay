"""Shared pytest fixtures.

Provides a test :class:`AwsSettings`, a moto-mocked :class:`ClientFactory`,
and per-service fixtures. All AWS calls run against moto's in-memory mock, so
no real credentials or network access are involved.
"""

from collections.abc import Iterator

import pytest
from moto import mock_aws

from cloud_relay.services.aws._core import AwsSettings, ClientFactory


@pytest.fixture
def aws_settings() -> AwsSettings:
    """Test AWS settings pinned to a commercial region."""
    return AwsSettings(region="us-east-1")


@pytest.fixture
def factory(aws_settings: AwsSettings) -> Iterator[ClientFactory]:
    """An AWS client factory whose calls are mocked by moto."""
    with mock_aws():
        yield ClientFactory(aws_settings)
