"""API tests for Secrets Manager routes using moto + FastAPI TestClient."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

from cloud_relay.api import deps
from cloud_relay.api.main import app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    # _build_aws_factory() reads settings directly, so configure via env, then
    # clear the cached factory so it is rebuilt under moto with this region.
    monkeypatch.setenv("CLOUD_RELAY_REGION", "us-east-1")
    deps.reset_aws_factory_cache()
    with mock_aws(), TestClient(app) as c:
        yield c
    deps.reset_aws_factory_cache()


def test_healthz(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}


def test_create_then_get(client: TestClient) -> None:
    r = client.post(
        "/aws/secrets-manager/secrets",
        json={"name": "api/tok", "secret_string": "s3cr3t"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "api/tok"

    g = client.post(
        "/aws/secrets-manager/secrets:get-value", json={"secret_id": "api/tok"}
    )
    assert g.status_code == 200
    # Masked by default (API does not pass show_secret context).
    assert g.json()["secret_string"] == "***"


def test_missing_maps_to_404(client: TestClient) -> None:
    r = client.post(
        "/aws/secrets-manager/secrets:get-value", json={"secret_id": "absent"}
    )
    assert r.status_code == 404
    assert r.json()["error"] == "ResourceNotFoundError"
