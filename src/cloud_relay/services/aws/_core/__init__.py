"""AWS-specific shared machinery.

Anything boto3-flavored that more than one AWS service needs lives here:

- :class:`AwsSettings` -- region, profile, retry policy, endpoint override
- :class:`ClientFactory` -- the sole point that calls ``boto3.client(...)``
- :class:`BaseService` -- shared base class for every ``*Service``
- :func:`translate_error` -- botocore ``ClientError`` -> domain exception

This package is private to ``cloud_relay.services.aws`` (the leading underscore
signals that); other clouds get their own ``_core`` package.
"""

from cloud_relay.services.aws._core.auth import ClientFactory
from cloud_relay.services.aws._core.config import AwsSettings, get_aws_settings
from cloud_relay.services.aws._core.errors import translate_error
from cloud_relay.services.aws._core.service import BaseService

__all__ = [
    "AwsSettings",
    "BaseService",
    "ClientFactory",
    "get_aws_settings",
    "translate_error",
]
