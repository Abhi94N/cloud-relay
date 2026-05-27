"""AWS Secrets Manager service wrapper.

This is the reference implementation that every other AWS service mirrors.
Each method validates its inputs via Pydantic request models, calls the boto3
client, translates any :class:`~botocore.exceptions.ClientError` into a domain
exception, and returns a typed response model.

Availability: all operations here exist in both AWS commercial and GovCloud.
"""

from botocore.exceptions import ClientError

from cloud_relay.services.aws._core import BaseService, translate_error
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


class SecretsManagerService(BaseService):
    """Typed wrapper over the boto3 ``secretsmanager`` client."""

    service_name = "secretsmanager"

    def get_secret_value(self, req: GetSecretValueRequest) -> SecretValue:
        """Fetch a secret's value.

        Args:
            req: The secret id/ARN and optional version selectors.

        Returns:
            The secret value (string or binary) with identifying metadata.

        Raises:
            ResourceNotFoundError: If the secret does not exist.
        """
        kwargs: dict[str, str] = {"SecretId": req.secret_id}
        if req.version_id:
            kwargs["VersionId"] = req.version_id
        if req.version_stage:
            kwargs["VersionStage"] = req.version_stage
        try:
            r = self._client.get_secret_value(**kwargs)
        except ClientError as e:
            raise translate_error(e) from e
        return SecretValue(
            name=r["Name"],
            arn=r["ARN"],
            version_id=r["VersionId"],
            secret_string=r.get("SecretString"),
            secret_binary=r.get("SecretBinary"),
            created_date=r.get("CreatedDate"),
        )

    def create_secret(self, req: CreateSecretRequest) -> CreateSecretResponse:
        """Create a new secret.

        Args:
            req: Name, value (string or binary), and optional description,
                KMS key, and tags.

        Returns:
            The new secret's name, ARN, and initial version id.

        Raises:
            ConflictError: If a secret with the same name already exists.
        """
        kwargs: dict[str, object] = {"Name": req.name}
        if req.secret_string is not None:
            kwargs["SecretString"] = req.secret_string.get_secret_value()
        if req.secret_binary is not None:
            kwargs["SecretBinary"] = req.secret_binary
        if req.description:
            kwargs["Description"] = req.description
        if req.kms_key_id:
            kwargs["KmsKeyId"] = req.kms_key_id
        if req.tags:
            kwargs["Tags"] = [{"Key": k, "Value": v} for k, v in req.tags.items()]
        try:
            r = self._client.create_secret(**kwargs)
        except ClientError as e:
            raise translate_error(e) from e
        return CreateSecretResponse(
            name=r["Name"], arn=r["ARN"], version_id=r["VersionId"]
        )

    def put_secret_value(self, req: PutSecretValueRequest) -> CreateSecretResponse:
        """Store a new version of an existing secret's value.

        Args:
            req: The secret id and the new value (string or binary).

        Returns:
            The secret's name, ARN, and the new version id.

        Raises:
            ResourceNotFoundError: If the secret does not exist.
        """
        kwargs: dict[str, object] = {"SecretId": req.secret_id}
        if req.secret_string is not None:
            kwargs["SecretString"] = req.secret_string.get_secret_value()
        if req.secret_binary is not None:
            kwargs["SecretBinary"] = req.secret_binary
        try:
            r = self._client.put_secret_value(**kwargs)
        except ClientError as e:
            raise translate_error(e) from e
        return CreateSecretResponse(
            name=r["Name"], arn=r["ARN"], version_id=r["VersionId"]
        )

    def describe_secret(self, secret_id: str) -> SecretMetadata:
        """Fetch a secret's metadata without its value.

        Args:
            secret_id: The secret name or ARN.

        Returns:
            Descriptive metadata for the secret.

        Raises:
            ResourceNotFoundError: If the secret does not exist.
        """
        try:
            r = self._client.describe_secret(SecretId=secret_id)
        except ClientError as e:
            raise translate_error(e) from e
        return SecretMetadata(
            name=r["Name"],
            arn=r["ARN"],
            description=r.get("Description"),
            kms_key_id=r.get("KmsKeyId"),
            rotation_enabled=r.get("RotationEnabled", False),
            last_changed_date=r.get("LastChangedDate"),
            last_accessed_date=r.get("LastAccessedDate"),
            tags={t["Key"]: t["Value"] for t in r.get("Tags", [])},
        )

    def list_secrets(self, req: ListSecretsRequest) -> list[SecretMetadata]:
        """List secrets, transparently following pagination.

        Args:
            req: Optional name-prefix filter and an optional cap on results.

        Returns:
            Metadata for each matching secret, up to ``req.max_results`` if set.
        """
        paginator = self._client.get_paginator("list_secrets")
        paginate_kwargs: dict[str, object] = {}
        if req.name_prefix:
            paginate_kwargs["Filters"] = [{"Key": "name", "Values": [req.name_prefix]}]
        out: list[SecretMetadata] = []
        try:
            for page in paginator.paginate(**paginate_kwargs):
                for s in page.get("SecretList", []):
                    out.append(
                        SecretMetadata(
                            name=s["Name"],
                            arn=s["ARN"],
                            description=s.get("Description"),
                            kms_key_id=s.get("KmsKeyId"),
                            rotation_enabled=s.get("RotationEnabled", False),
                            last_changed_date=s.get("LastChangedDate"),
                            last_accessed_date=s.get("LastAccessedDate"),
                            tags={t["Key"]: t["Value"] for t in s.get("Tags", [])},
                        )
                    )
                    if req.max_results and len(out) >= req.max_results:
                        return out[: req.max_results]
        except ClientError as e:
            raise translate_error(e) from e
        return out

    def delete_secret(self, req: DeleteSecretRequest) -> DeleteSecretResponse:
        """Delete a secret, optionally forcing immediate deletion.

        Args:
            req: The secret id and either a recovery window or a force flag.

        Returns:
            The deleted secret's name, ARN, and scheduled deletion date.

        Raises:
            ResourceNotFoundError: If the secret does not exist.
        """
        kwargs: dict[str, object] = {"SecretId": req.secret_id}
        if req.force_delete:
            kwargs["ForceDeleteWithoutRecovery"] = True
        elif req.recovery_window_days is not None:
            kwargs["RecoveryWindowInDays"] = req.recovery_window_days
        try:
            r = self._client.delete_secret(**kwargs)
        except ClientError as e:
            raise translate_error(e) from e
        return DeleteSecretResponse(
            name=r["Name"], arn=r["ARN"], deletion_date=r.get("DeletionDate")
        )
