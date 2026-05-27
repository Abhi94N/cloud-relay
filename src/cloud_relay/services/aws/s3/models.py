"""Pydantic models for the S3 service wrapper.

Only the models backing the implemented operation (``head_object``) are defined.
When extending the service, add the matching request/response models here,
following the same shape. See ``EXTENDING.md`` in this package.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class HeadObjectRequest(BaseModel):
    """Parameters for an S3 ``HeadObject`` call."""

    bucket: str = Field(..., description="Bucket name")
    key: str = Field(..., description="Object key")
    version_id: str | None = Field(default=None, description="Object version id")


class HeadObjectResponse(BaseModel):
    """Metadata returned by ``HeadObject`` (no object body).

    ``storage_class``, ``restore``, and ``archive_status`` are present when the
    object lives in a non-Standard tier or is being restored from Glacier. They
    are absent (``None``) for plain Standard objects, since S3 omits the
    ``StorageClass`` header for the default tier.
    """

    content_length: int
    content_type: str
    etag: str
    last_modified: datetime
    metadata: dict[str, str] = Field(default_factory=dict)
    storage_class: str | None = Field(
        default=None,
        description="STANDARD, INTELLIGENT_TIERING, GLACIER, DEEP_ARCHIVE, etc.",
    )
    restore: str | None = Field(
        default=None,
        description='S3 Restore header (e.g. ongoing-request="false", expiry-date=...)',
    )
    archive_status: str | None = Field(
        default=None,
        description="ARCHIVE_ACCESS or DEEP_ARCHIVE_ACCESS for Intelligent-Tiering",
    )


# TODO(extend): add ListObjectsRequest / GetObjectRequest, etc. here as the
# service grows. Mirror the secrets_manager models for paginated list shapes.
