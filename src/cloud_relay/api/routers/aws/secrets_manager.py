"""HTTP routes for AWS Secrets Manager.

Routes are thin: they depend on the service, wrap the synchronous call in
``run_in_threadpool`` so the event loop stays free, and let the global exception
handler in :mod:`cloud_relay.api.main` translate domain errors to HTTP codes.

Secret values are accepted only in request bodies (never path/query) so they do
not appear in access logs.
"""

from fastapi import APIRouter, Depends, status
from fastapi.concurrency import run_in_threadpool

from cloud_relay.api.deps import get_secrets_manager_service
from cloud_relay.services.aws.secrets_manager import (
    CreateSecretRequest,
    CreateSecretResponse,
    DeleteSecretRequest,
    DeleteSecretResponse,
    GetSecretValueRequest,
    ListSecretsRequest,
    PutSecretValueRequest,
    SecretMetadata,
    SecretsManagerService,
    SecretValue,
)

router = APIRouter(prefix="/aws/secrets-manager", tags=["aws:secrets-manager"])


@router.post("/secrets:get-value", response_model=SecretValue)
async def get_secret_value(
    req: GetSecretValueRequest,
    svc: SecretsManagerService = Depends(get_secrets_manager_service),
) -> SecretValue:
    """Fetch a secret's value."""
    return await run_in_threadpool(svc.get_secret_value, req)


@router.post(
    "/secrets",
    response_model=CreateSecretResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_secret(
    req: CreateSecretRequest,
    svc: SecretsManagerService = Depends(get_secrets_manager_service),
) -> CreateSecretResponse:
    """Create a new secret."""
    return await run_in_threadpool(svc.create_secret, req)


@router.put("/secrets:put-value", response_model=CreateSecretResponse)
async def put_secret_value(
    req: PutSecretValueRequest,
    svc: SecretsManagerService = Depends(get_secrets_manager_service),
) -> CreateSecretResponse:
    """Store a new version of an existing secret's value."""
    return await run_in_threadpool(svc.put_secret_value, req)


@router.get("/secrets/{secret_id}", response_model=SecretMetadata)
async def describe_secret(
    secret_id: str,
    svc: SecretsManagerService = Depends(get_secrets_manager_service),
) -> SecretMetadata:
    """Return a secret's metadata (no value)."""
    return await run_in_threadpool(svc.describe_secret, secret_id)


@router.post("/secrets:list", response_model=list[SecretMetadata])
async def list_secrets(
    req: ListSecretsRequest,
    svc: SecretsManagerService = Depends(get_secrets_manager_service),
) -> list[SecretMetadata]:
    """List secrets, optionally filtered by name prefix."""
    return await run_in_threadpool(svc.list_secrets, req)


@router.post("/secrets:delete", response_model=DeleteSecretResponse)
async def delete_secret(
    req: DeleteSecretRequest,
    svc: SecretsManagerService = Depends(get_secrets_manager_service),
) -> DeleteSecretResponse:
    """Delete a secret."""
    return await run_in_threadpool(svc.delete_secret, req)
