"""Tests for the cloud-neutral Settings."""

from cloud_relay.core.config import Settings, get_settings


def test_default_log_level() -> None:
    assert Settings().log_level == "INFO"


def test_env_prefix(monkeypatch) -> None:
    monkeypatch.setenv("CLOUD_RELAY_LOG_LEVEL", "DEBUG")
    assert Settings().log_level == "DEBUG"


def test_get_settings_returns_fresh_instance() -> None:
    assert isinstance(get_settings(), Settings)
