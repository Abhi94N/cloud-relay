"""Tests for the output formatter registry and secret masking."""

import json

import pytest

from cloud_relay.cli.output import available_formats, render
from cloud_relay.services.aws.secrets_manager import SecretValue


def _sample() -> SecretValue:
    return SecretValue(name="n", arn="arn", version_id="v1", secret_string="topsecret")


def test_formats_registered() -> None:
    assert set(available_formats()) == {"json", "table", "yaml"}


def test_json_masks_by_default() -> None:
    out = json.loads(render(_sample(), "json"))
    assert out["secret_string"] == "***"


def test_json_reveals_with_flag() -> None:
    out = json.loads(render(_sample(), "json", show_secret=True))
    assert out["secret_string"] == "topsecret"


def test_yaml_renders() -> None:
    assert "name: n" in render(_sample(), "yaml")


def test_table_renders_list() -> None:
    out = render([_sample()], "table")
    assert "name" in out


def test_unknown_format_raises() -> None:
    with pytest.raises(ValueError):
        render(_sample(), "xml")
