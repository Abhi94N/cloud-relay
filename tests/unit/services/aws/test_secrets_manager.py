"""Tests for the Secrets Manager service against moto."""

import pytest

from cloud_relay.core.errors import ResourceNotFoundError
from cloud_relay.services.aws.secrets_manager import (
    CreateSecretRequest,
    DeleteSecretRequest,
    GetSecretValueRequest,
    ListSecretsRequest,
    PutSecretValueRequest,
    SecretsManagerService,
)


@pytest.fixture
def svc(factory) -> SecretsManagerService:
    return SecretsManagerService(factory)


def test_create_and_get(svc: SecretsManagerService) -> None:
    svc.create_secret(CreateSecretRequest(name="db/pw", secret_string="hunter2"))
    got = svc.get_secret_value(GetSecretValueRequest(secret_id="db/pw"))
    assert got.name == "db/pw"
    assert got.secret_string is not None
    assert got.secret_string.get_secret_value() == "hunter2"


def test_get_missing_raises(svc: SecretsManagerService) -> None:
    with pytest.raises(ResourceNotFoundError):
        svc.get_secret_value(GetSecretValueRequest(secret_id="nope"))


def test_put_new_version(svc: SecretsManagerService) -> None:
    svc.create_secret(CreateSecretRequest(name="api/key", secret_string="v1"))
    svc.put_secret_value(
        PutSecretValueRequest(secret_id="api/key", secret_string="v2")
    )
    got = svc.get_secret_value(GetSecretValueRequest(secret_id="api/key"))
    assert got.secret_string is not None
    assert got.secret_string.get_secret_value() == "v2"


def test_describe(svc: SecretsManagerService) -> None:
    svc.create_secret(
        CreateSecretRequest(name="svc/token", secret_string="x", description="desc")
    )
    meta = svc.describe_secret("svc/token")
    assert meta.name == "svc/token"
    assert meta.description == "desc"


def test_list_and_prefix(svc: SecretsManagerService) -> None:
    svc.create_secret(CreateSecretRequest(name="app/one", secret_string="1"))
    svc.create_secret(CreateSecretRequest(name="app/two", secret_string="2"))
    svc.create_secret(CreateSecretRequest(name="other/three", secret_string="3"))
    all_secrets = svc.list_secrets(ListSecretsRequest())
    assert len(all_secrets) >= 3
    capped = svc.list_secrets(ListSecretsRequest(max_results=1))
    assert len(capped) == 1


def test_delete(svc: SecretsManagerService) -> None:
    svc.create_secret(CreateSecretRequest(name="temp/del", secret_string="x"))
    res = svc.delete_secret(
        DeleteSecretRequest(secret_id="temp/del", force_delete=True)
    )
    assert res.name == "temp/del"


def test_create_requires_exactly_one_value() -> None:
    with pytest.raises(ValueError):
        CreateSecretRequest(name="bad")  # neither string nor binary


def test_delete_window_xor_force() -> None:
    with pytest.raises(ValueError):
        DeleteSecretRequest(secret_id="x", force_delete=True, recovery_window_days=7)
