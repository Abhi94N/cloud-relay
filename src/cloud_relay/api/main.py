"""FastAPI application factory and global error handling.

Mounts one router per service (grouped by cloud) and installs a single
exception handler that maps the domain exception hierarchy
(:mod:`cloud_relay.core.errors`) onto HTTP status codes. This is what keeps
routers thin -- they never translate errors themselves.

Logging is configured once at app startup via the ``lifespan`` context so
``CLOUD_RELAY_LOG_LEVEL`` actually takes effect.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from cloud_relay.api.routers.aws import s3, secrets_manager
from cloud_relay.core.config import get_settings
from cloud_relay.core.errors import (
    AccessDeniedError,
    CloudRelayError,
    ConflictError,
    ResourceNotFoundError,
    ThrottledError,
    ValidationError,
)
from cloud_relay.core.logging import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Configure logging on startup; nothing to tear down."""
    configure_logging(get_settings())
    yield


app = FastAPI(title="cloud-relay API", version="0.1.0", lifespan=lifespan)

app.include_router(secrets_manager.router)
app.include_router(s3.router)

# Domain exception -> HTTP status code. Order does not matter; isinstance is
# checked against each. Unmapped CloudRelayError subclasses fall back to 502.
_STATUS: dict[type[CloudRelayError], int] = {
    ResourceNotFoundError: 404,
    AccessDeniedError: 403,
    ConflictError: 409,
    ValidationError: 422,
    ThrottledError: 429,
}


@app.exception_handler(CloudRelayError)
async def _handle_domain_error(request: Request, exc: CloudRelayError) -> JSONResponse:
    """Translate a domain exception into a structured JSON error response."""
    status_code = next(
        (code for cls, code in _STATUS.items() if isinstance(exc, cls)), 502
    )
    return JSONResponse(
        status_code=status_code,
        content={"error": type(exc).__name__, "detail": str(exc)},
    )


@app.get("/healthz", tags=["meta"])
async def healthz() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}
