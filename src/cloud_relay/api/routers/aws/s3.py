"""HTTP routes for AWS S3 (scaffold).

``head-object`` is implemented; extend by mirroring it. See
``services/aws/s3/EXTENDING.md``.
"""

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from cloud_relay.api.deps import get_s3_service
from cloud_relay.services.aws.s3 import (
    HeadObjectRequest,
    HeadObjectResponse,
    S3Service,
)

router = APIRouter(prefix="/aws/s3", tags=["aws:s3"])


@router.post("/objects:head", response_model=HeadObjectResponse)
async def head_object(
    req: HeadObjectRequest,
    svc: S3Service = Depends(get_s3_service),
) -> HeadObjectResponse:
    """Return object metadata without downloading the body."""
    return await run_in_threadpool(svc.head_object, req)
