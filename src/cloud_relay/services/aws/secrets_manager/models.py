"""Pydantic request/response models for AWS Secrets Manager.

These models are the shared contract used by both adapters: FastAPI uses them
as request/response schemas, and the CLI uses them for input validation and
output serialization. Models hold data and validation only -- no behavior.

Sensitive values use :class:`pydantic.SecretStr`, which renders as ``'**********'``
in reprs and logs. The CLI formatters reveal the underlying value only when the
caller explicitly passes ``--show-secret`` (threaded through Pydantic's
serialization ``context``); see :mod:`cloud_relay.cli.output`.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, SecretStr, field_serializer, model_validator


class GetSecretValueRequest(BaseModel):
    """Parameters for fetching a secret's value."""

    secret_id: str = Field(..., description="Secret name or ARN")
    version_id: str | None = Field(default=None, description="Specific version id")
    version_stage: str | None = Field(default=None, description="Staging label")


class SecretValue(BaseModel):
    """A secret's value plus identifying metadata.

    Exactly one of :attr:`secret_string` / :attr:`secret_binary` is populated,
    matching how the secret was stored.
    """

    name: str
    arn: str
    version_id: str
    secret_string: SecretStr | None = None
    secret_binary: bytes | None = None
    created_date: datetime | None = None

    @field_serializer("secret_string", when_used="json")
    def _reveal_if_requested(self, value: SecretStr | None, info: Any) -> str | None:
        """Reveal the secret string only when ``show_secret`` context is set.

        The CLI passes ``context={"show_secret": True}`` to ``model_dump`` when
        the user opts in with ``--show-secret``; otherwise the value is masked.
        """
        if value is None:
            return None
        ctx = info.context or {}
        if ctx.get("show_secret"):
            return value.get_secret_value()
        return "***"


class CreateSecretRequest(BaseModel):
    """Parameters for creating a new secret.

    Exactly one of :attr:`secret_string` / :attr:`secret_binary` must be set.
    """

    name: str
    secret_string: SecretStr | None = None
    secret_binary: bytes | None = None
    description: str | None = None
    kms_key_id: str | None = None
    tags: dict[str, str] | None = None

    @model_validator(mode="after")
    def _exactly_one_value(self) -> "CreateSecretRequest":
        if (self.secret_string is None) == (self.secret_binary is None):
            raise ValueError(
                "exactly one of secret_string or secret_binary is required"
            )
        return self


class PutSecretValueRequest(BaseModel):
    """Parameters for storing a new version of an existing secret's value.

    Exactly one of :attr:`secret_string` / :attr:`secret_binary` must be set.
    """

    secret_id: str
    secret_string: SecretStr | None = None
    secret_binary: bytes | None = None

    @model_validator(mode="after")
    def _exactly_one_value(self) -> "PutSecretValueRequest":
        if (self.secret_string is None) == (self.secret_binary is None):
            raise ValueError(
                "exactly one of secret_string or secret_binary is required"
            )
        return self


class SecretMetadata(BaseModel):
    """Descriptive metadata for a secret (never includes the value)."""

    name: str
    arn: str
    description: str | None = None
    kms_key_id: str | None = None
    rotation_enabled: bool = False
    last_changed_date: datetime | None = None
    last_accessed_date: datetime | None = None
    tags: dict[str, str] = Field(default_factory=dict)


class ListSecretsRequest(BaseModel):
    """Parameters for listing secrets."""

    name_prefix: str | None = Field(default=None, description="Filter by name prefix")
    max_results: int | None = Field(
        default=None, ge=1, description="Cap on total results returned"
    )


class CreateSecretResponse(BaseModel):
    """Identifiers returned after creating or updating a secret value."""

    name: str
    arn: str
    version_id: str


class DeleteSecretRequest(BaseModel):
    """Parameters for deleting a secret.

    :attr:`recovery_window_days` and :attr:`force_delete` are mutually exclusive.
    """

    secret_id: str
    recovery_window_days: int | None = Field(default=None, ge=7, le=30)
    force_delete: bool = False

    @model_validator(mode="after")
    def _window_xor_force(self) -> "DeleteSecretRequest":
        if self.force_delete and self.recovery_window_days is not None:
            raise ValueError(
                "recovery_window_days and force_delete are mutually exclusive"
            )
        return self


class DeleteSecretResponse(BaseModel):
    """Result of a delete request."""

    name: str
    arn: str
    deletion_date: datetime | None = None
