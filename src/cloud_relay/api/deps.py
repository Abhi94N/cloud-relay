"""FastAPI dependency providers, grouped by cloud provider.

These wire ``AwsSettings`` -> :class:`ClientFactory` -> service instances into
route handlers via ``Depends``. The factory is built once per process and reused
across requests so a single boto3 session is shared.

When a new cloud is added, follow the same pattern: a cached
``_build_<cloud>_factory()`` builder, a ``reset_<cloud>_factory_cache()`` for
tests, and ``get_<svc>_service`` providers for each service.
"""

from functools import lru_cache

from fastapi import Depends

from cloud_relay.services.aws._core import ClientFactory, get_aws_settings
from cloud_relay.services.aws.s3 import S3Service
from cloud_relay.services.aws.secrets_manager import SecretsManagerService


@lru_cache(maxsize=1)
def _build_aws_factory() -> ClientFactory:
    """Build the process-wide AWS client factory once.

    Note:
        :class:`~cloud_relay.services.aws._core.config.AwsSettings` is not
        hashable, so it cannot be an ``lru_cache`` argument. Settings are
        resolved *inside* this cached, no-argument builder instead. Tests that
        override settings should call :func:`reset_aws_factory_cache` first.
    """
    return ClientFactory(get_aws_settings())


def reset_aws_factory_cache() -> None:
    """Clear the cached AWS factory. Intended for tests that swap settings."""
    _build_aws_factory.cache_clear()


def get_aws_factory() -> ClientFactory:
    """Provide the process-wide AWS client factory."""
    return _build_aws_factory()


def get_secrets_manager_service(
    factory: ClientFactory = Depends(get_aws_factory),
) -> SecretsManagerService:
    """Provide a Secrets Manager service bound to the request's factory."""
    return SecretsManagerService(factory)


def get_s3_service(
    factory: ClientFactory = Depends(get_aws_factory),
) -> S3Service:
    """Provide an S3 service bound to the request's factory."""
    return S3Service(factory)
