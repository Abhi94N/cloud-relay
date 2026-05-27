"""AWS S3 wrapper (scaffold): service class and implemented models."""

from cloud_relay.services.aws.s3.exceptions import ObjectNotFoundError
from cloud_relay.services.aws.s3.models import HeadObjectRequest, HeadObjectResponse
from cloud_relay.services.aws.s3.service import S3Service

__all__ = [
    "HeadObjectRequest",
    "HeadObjectResponse",
    "ObjectNotFoundError",
    "S3Service",
]
