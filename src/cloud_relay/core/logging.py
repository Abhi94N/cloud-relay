"""Logging setup for cloud-relay.

Uses the Python standard library :mod:`logging` only. Rich formatting is a CLI
presentation concern and lives in :mod:`cloud_relay.cli.output`, never here, so
that importing the library or running the API pulls in no CLI dependencies.
"""

import logging

from cloud_relay.core.config import Settings

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging(settings: Settings) -> None:
    """Configure root logging from :class:`Settings`.

    Idempotent enough for app startup; call once early in the API lifespan or
    at CLI invocation. Honors ``settings.log_level``.

    Args:
        settings: Configuration providing the desired log level.
    """
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format=_LOG_FORMAT,
    )


def get_logger(name: str) -> logging.Logger:
    """Return a named logger.

    Args:
        name: Logger name, conventionally the module ``__name__``.

    Returns:
        A standard library :class:`logging.Logger`.
    """
    return logging.getLogger(name)
