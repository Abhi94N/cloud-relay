"""CLI tests for Secrets Manager commands using moto + Typer CliRunner."""

import json
from collections.abc import Iterator

import pytest
from moto import mock_aws
from typer.testing import CliRunner

from cloud_relay.cli.main import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _mock_aws(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("CLOUD_RELAY_REGION", "us-east-1")
    with mock_aws():
        yield


def test_create_and_list_json() -> None:
    create = runner.invoke(
        app, ["aws", "secrets-manager", "create", "cli/one", "--value", "v"]
    )
    assert create.exit_code == 0, create.output

    listed = runner.invoke(app, ["aws", "secrets-manager", "list"])
    assert listed.exit_code == 0
    data = json.loads(listed.output)
    assert any(s["name"] == "cli/one" for s in data)


def test_get_value_masked_then_revealed() -> None:
    runner.invoke(
        app, ["aws", "secrets-manager", "create", "cli/two", "--value", "shh"]
    )

    masked = runner.invoke(app, ["aws", "secrets-manager", "get-value", "cli/two"])
    assert json.loads(masked.output)["secret_string"] == "***"

    revealed = runner.invoke(
        app, ["aws", "secrets-manager", "get-value", "cli/two", "--show-secret"]
    )
    assert json.loads(revealed.output)["secret_string"] == "shh"
