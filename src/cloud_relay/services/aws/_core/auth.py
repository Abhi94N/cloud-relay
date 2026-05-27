"""boto3 session and client construction.

:class:`ClientFactory` is the *single* place in the AWS package where boto3
clients are created. Every AWS service obtains its client from a factory, and
no module-level or global clients exist anywhere else. This keeps credential
and region resolution in one auditable location and makes testing (and
per-request or multi-account scenarios) straightforward.
"""

from typing import Any

import boto3
from botocore.config import Config as BotoConfig

from cloud_relay.services.aws._core.config import AwsSettings


class ClientFactory:
    """Builds and caches boto3 clients from an :class:`AwsSettings` instance.

    One factory wraps one boto3 :class:`~boto3.session.Session`. Clients are
    created lazily on first request and cached by service name, so repeated
    lookups for the same service return the same client.

    Example:
        >>> from cloud_relay.services.aws._core.config import AwsSettings
        >>> factory = ClientFactory(AwsSettings(region="us-east-1"))
        >>> sm = factory.client("secretsmanager")
    """

    def __init__(self, settings: AwsSettings) -> None:
        """Initialize the factory and build the underlying boto3 session.

        Args:
            settings: AWS configuration controlling region, profile, retries,
                and (for tests) an optional endpoint override.
        """
        self._settings = settings
        self._session = self._build_session()
        self._clients: dict[str, Any] = {}

    def _build_session(self) -> boto3.Session:
        """Construct the boto3 session, applying profile/region if configured."""
        kwargs: dict[str, Any] = {}
        if self._settings.profile:
            kwargs["profile_name"] = self._settings.profile
        if self._settings.region:
            kwargs["region_name"] = self._settings.region
        return boto3.Session(**kwargs)

    def _boto_config(self) -> BotoConfig:
        """Build the botocore client config (retry policy)."""
        return BotoConfig(
            retries={
                "max_attempts": self._settings.max_retries,
                "mode": self._settings.retry_mode,
            }  # type: ignore[arg-type]
        )

    def client(self, service_name: str) -> Any:
        """Return a cached boto3 client for the given AWS service.

        Args:
            service_name: The boto3 service identifier, e.g. ``"secretsmanager"``
                or ``"s3"``.

        Returns:
            A boto3 client, created on first call and cached thereafter.

        Note:
            ``service_name`` is a runtime ``str`` rather than one of the boto3
            per-service ``Literal`` overloads, so the call is deliberately typed
            loosely; the public return type is ``Any`` by design (callers get
            their own typed stubs at use sites if desired).
        """
        if service_name not in self._clients:
            client = self._session.client(  # type: ignore[call-overload]
                service_name,
                config=self._boto_config(),
                endpoint_url=self._settings.endpoint_url,
            )
            self._clients[service_name] = client
        return self._clients[service_name]
