"""Tests for AwsSettings (region/profile/retries)."""

from cloud_relay.services.aws._core import AwsSettings, get_aws_settings


def test_defaults_have_no_hardcoded_region() -> None:
    s = AwsSettings()
    assert s.region is None  # keeps GovCloud resolution working
    assert s.max_retries == 3
    assert s.retry_mode == "standard"


def test_env_prefix(monkeypatch) -> None:
    monkeypatch.setenv("CLOUD_RELAY_REGION", "us-gov-west-1")
    s = AwsSettings()
    assert s.region == "us-gov-west-1"


def test_inherits_log_level_from_core(monkeypatch) -> None:
    monkeypatch.setenv("CLOUD_RELAY_LOG_LEVEL", "WARNING")
    assert AwsSettings().log_level == "WARNING"


def test_get_aws_settings_returns_fresh_instance() -> None:
    assert isinstance(get_aws_settings(), AwsSettings)
