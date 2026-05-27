"""AWS S3 service wrapper (scaffold).

This service demonstrates the
:class:`~cloud_relay.services.aws._core.service.BaseService` pattern with one
fully-implemented operation, ``head_object``. The remaining operations are
intentional stubs that raise :class:`NotImplementedError` with a pointer to the
reference implementation -- see ``EXTENDING.md`` in this package for the
four-step process to add a new operation.
"""

from typing import Any

from botocore.exceptions import ClientError

from cloud_relay.services.aws._core import BaseService, translate_error
from cloud_relay.services.aws.s3.models import HeadObjectRequest, HeadObjectResponse


class S3Service(BaseService):
    """Typed wrapper over the boto3 ``s3`` client."""

    service_name = "s3"

    def head_object(self, req: HeadObjectRequest) -> HeadObjectResponse:
        """Fetch object metadata without downloading the body.

        Args:
            req: Bucket, key, and optional version id.

        Returns:
            The object's size, content type, ETag, modified time, and metadata.

        Raises:
            ResourceNotFoundError: If the bucket or object does not exist.
        """
        kwargs: dict[str, str] = {"Bucket": req.bucket, "Key": req.key}
        if req.version_id:
            kwargs["VersionId"] = req.version_id
        try:
            r = self._client.head_object(**kwargs)
        except ClientError as e:
            raise translate_error(e) from e
        return HeadObjectResponse(
            content_length=r["ContentLength"],
            content_type=r.get("ContentType", ""),
            etag=r["ETag"],
            last_modified=r["LastModified"],
            metadata=r.get("Metadata", {}),
            storage_class=r.get("StorageClass"),
            restore=r.get("Restore"),
            archive_status=r.get("ArchiveStatus"),
        )

    def list_objects(self, req: Any) -> Any:
        """List objects in a bucket. **Not yet implemented.**

        To implement: add ``ListObjectsRequest``/``ListObjectsResponse`` models,
        then use the boto3 paginator ``"list_objects_v2"``. The pagination
        pattern to copy lives in
        :meth:`cloud_relay.services.aws.secrets_manager.service.SecretsManagerService.list_secrets`.
        """
        raise NotImplementedError(
            "s3.list_objects not implemented -- see SecretsManagerService.list_secrets "
            "for the paginator pattern, and EXTENDING.md for the steps"
        )

    def get_object(self, req: Any) -> Any:
        """Download an object. **Not yet implemented.**

        To implement: add the request/response models and call ``get_object``,
        deciding whether to stream the body or return bytes.
        """
        raise NotImplementedError("s3.get_object not implemented -- see EXTENDING.md")
