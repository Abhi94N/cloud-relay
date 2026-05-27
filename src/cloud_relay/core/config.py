"""Cloud-neutral runtime configuration for cloud-relay.

:class:`Settings` holds only the configuration that is meaningful across every
cloud provider. Today that is just ``log_level``. Per-cloud configuration (AWS
region/profile, GCP project, Azure tenant, ...) lives in each provider's own
settings class that *inherits* from this base -- see
:class:`cloud_relay.services.aws._core.config.AwsSettings`.

Configuration precedence
-------------------------
Values may be supplied (highest priority first) by constructor arguments,
environment variables prefixed ``CLOUD_RELAY_`` (e.g. ``CLOUD_RELAY_LOG_LEVEL``),
or a local ``.env`` file.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Cloud-neutral application configuration.

    Provider-specific settings classes inherit from this one and add their own
    fields. The shared ``CLOUD_RELAY_`` env prefix is inherited automatically.

    Attributes:
        log_level: Root log level for
            :func:`cloud_relay.core.logging.configure_logging`.
    """

    model_config = SettingsConfigDict(
        env_prefix="CLOUD_RELAY_",
        env_file=".env",
        extra="ignore",
    )

    log_level: str = Field(default="INFO")


def get_settings() -> Settings:
    """Return a fresh cloud-neutral :class:`Settings` instance."""
    return Settings()
