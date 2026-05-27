"""Tests for the S3 scaffold service against moto."""

import pytest

from cloud_relay.core.errors import ResourceNotFoundError
from cloud_relay.services.aws.s3 import HeadObjectRequest, S3Service


@pytest.fixture
def svc(factory) -> S3Service:
    return S3Service(factory)


def test_head_object(svc: S3Service, factory) -> None:
    s3 = factory.client("s3")
    s3.create_bucket(Bucket="test-bucket")
    s3.put_object(
        Bucket="test-bucket", Key="k.txt", Body=b"hello", ContentType="text/plain"
    )
    res = svc.head_object(HeadObjectRequest(bucket="test-bucket", key="k.txt"))
    assert res.content_length == 5
    assert res.content_type == "text/plain"
    # Standard tier is the default; restore/archive_status are absent.
    assert res.restore is None
    assert res.archive_status is None


def test_head_object_surfaces_storage_class(svc: S3Service, factory) -> None:
    s3 = factory.client("s3")
    s3.create_bucket(Bucket="tier-bucket")
    s3.put_object(
        Bucket="tier-bucket",
        Key="cold.bin",
        Body=b"x",
        StorageClass="GLACIER",
    )
    res = svc.head_object(HeadObjectRequest(bucket="tier-bucket", key="cold.bin"))
    assert res.storage_class == "GLACIER"


def test_head_missing_raises(svc: S3Service, factory) -> None:
    factory.client("s3").create_bucket(Bucket="test-bucket-2")
    with pytest.raises(ResourceNotFoundError):
        svc.head_object(HeadObjectRequest(bucket="test-bucket-2", key="absent"))


def test_stub_raises_not_implemented(svc: S3Service) -> None:
    with pytest.raises(NotImplementedError):
        svc.list_objects(None)
