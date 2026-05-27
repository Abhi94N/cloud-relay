"""AWS-specific runtime configuration.

:class:`AwsSettings` extends :class:`cloud_relay.core.config.Settings` with the
fields boto3 needs (region, profile, retry policy, optional endpoint override).
Future cloud packages should add a parallel ``GcpSettings`` /
``AzureSettings`` in their own ``_core/config.py``.

AWS-native variables (``AWS_REGION``, ``AWS_PROFILE``, ...) are honored by
boto3 directly and need not be duplicated here.

GovCloud
--------
No region is hardcoded. When a ``us-gov-*`` region is supplied, boto3 resolves
the correct GovCloud endpoints automatically, so the wrapper works in both AWS
commercial and GovCloud with no extra code.
"""

from pydantic import Field

from cloud_relay.core.config import Settings


class AwsSettings(Settings):
    """AWS-specific configuration. Inherits ``log_level`` and env prefix.

    Attributes:
        region: Optional AWS region override. When ``None``, boto3's own
            resolution chain (env, shared config, instance profile / IRSA) is
            used unchanged. Supplying a ``us-gov-*`` region selects GovCloud.
        profile: Optional named AWS profile to use for credentials.
        endpoint_url: Optional endpoint override, used by tests and localstack.
        max_retries: Maximum botocore retry attempts per request.
        retry_mode: botocore retry mode: ``standard``, ``adaptive``, or ``legacy``.
    """

    region: str | None = Field(default=None, description="AWS region override")
    profile: str | None = Field(default=None, description="AWS named profile")
    endpoint_url: str | None = Field(
        default=None, description="Endpoint override (tests/localstack)"
    )
    max_retries: int = Field(default=3, ge=0)
    retry_mode: str = Field(default="standard")


def get_aws_settings() -> AwsSettings:
    """Return a fresh :class:`AwsSettings` instance."""
    return AwsSettings()
