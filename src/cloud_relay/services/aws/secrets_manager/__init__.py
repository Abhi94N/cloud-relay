"""AWS Secrets Manager wrapper: service class and public models.

Import everything you need from this package directly::

    from cloud_relay.services.aws.secrets_manager import (
        SecretsManagerService, GetSecretValueRequest,
    )
"""

from cloud_relay.services.aws.secrets_manager.exceptions import SecretNotFoundError
from cloud_relay.services.aws.secrets_manager.models import (
    CreateSecretRequest,
    CreateSecretResponse,
    DeleteSecretRequest,
    DeleteSecretResponse,
    GetSecretValueRequest,
    ListSecretsRequest,
    PutSecretValueRequest,
    SecretMetadata,
    SecretValue,
)
from cloud_relay.services.aws.secrets_manager.service import SecretsManagerService

__all__ = [
    "CreateSecretRequest",
    "CreateSecretResponse",
    "DeleteSecretRequest",
    "DeleteSecretResponse",
    "GetSecretValueRequest",
    "ListSecretsRequest",
    "PutSecretValueRequest",
    "SecretMetadata",
    "SecretNotFoundError",
    "SecretValue",
    "SecretsManagerService",
]
