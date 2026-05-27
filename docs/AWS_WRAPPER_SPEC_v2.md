# AWS Wrapper — Build Specification (v2)

A single repository that consolidates AWS service wrappers into one place. It is **primarily a library** of framework-agnostic service modules, with two thin adapters on top: a **Typer CLI** and a **FastAPI** HTTP surface. Other services (the monorepo, internal tooling, ops scripts) import the library directly; the CLI is for operators and debugging; the API exists for non-Python consumers or when AWS access should sit behind a service boundary.

This document is the complete build spec. Build bottom-up: `core/` first, then one fully-implemented service (Secrets Manager), then the adapters, then the scaffolded service (S3).

**v2 changes:** added a `BaseService` base class in `core/` that all services inherit (removes constructor boilerplate, enforces the service-name contract); replaced the single `output.py` with a class-based formatter package (`Formatter` protocol + per-format classes + registry). Directory separation tightened so each package has one statable responsibility.

---

## 1. Guiding principles (do not violate)

1. **Services are framework-agnostic.** Code under `src/aws_wrapper/services/` MUST NOT import FastAPI, Typer, Rich, or anything HTTP/CLI-shaped. It imports only boto3, Pydantic, and `core/`.
2. **Adapters are thin.** Routers (`api/`) and commands (`cli/`) parse input, call a service method, and format output. No business logic, no `boto3.client()` calls, no retry logic in adapters. If an adapter grows past ~50 lines, logic has leaked out of the service layer — push it back down.
3. **CLI and API are peers.** `cli/` MUST NOT import from `api/` and vice versa. Both depend only on `services/` and `core/`.
4. **No global boto3 clients.** A single session/client factory lives in `core/auth.py`. Clients are constructed there and injected — into the API via `Depends()`, into the CLI via a context object.
5. **Pydantic models are shared and pure.** Request/response models live in `services/<svc>/models.py`, used by both adapters. Models hold data and validators only — no behavior/methods beyond validation.
6. **Sync everywhere.** boto3 is synchronous. The service layer is sync. The CLI is sync end-to-end. API routes wrap sync service calls in `fastapi.concurrency.run_in_threadpool`. Do NOT introduce aioboto3.
7. **Region is never hardcoded.** Region/credentials flow from standard AWS config/env through `core/config.py`. This is what makes the wrapper work in both AWS commercial and GovCloud with no extra code (see §11).
8. **API shape is Option A:** one FastAPI app, one router per service, mounted under a service prefix. Structured so splitting into per-service apps later is mechanical.
9. **Classes where state lives; functions where transformation is pure.** Services, the client factory, settings, formatters, and the exception hierarchy are classes because they carry state or are a type family. Pure transforms (`translate_error`) stay functions. Do not force classes onto stateless logic.

---

## 2. Tooling & stack

| Concern        | Choice                                            |
|----------------|---------------------------------------------------|
| Packaging/deps | **uv** (uv-managed venv, `uv.lock`, `uv sync`)    |
| Lint + format  | **ruff** (lint and format)                        |
| Tests          | **pytest** + **moto** + **coverage**              |
| Runtime        | **Python 3.12** (min 3.11)                        |
| AWS SDK        | **boto3** + **botocore**                          |
| Models         | **Pydantic v2** + **pydantic-settings**           |
| CLI            | **Typer** (+ **Rich**)                            |
| API            | **FastAPI** (0.136.x) + **uvicorn**               |
| Type checking  | **mypy** (strict)                                 |

Dependency ranges (AWS SDK minor unpinned since it ships daily):

```
python      >= 3.11
boto3        >= 1.34
botocore     >= 1.34
pydantic     >= 2.7,<3
pydantic-settings >= 2.3,<3
typer        >= 0.12,<1
rich         >= 13.7
pyyaml       >= 6.0          # YamlFormatter
fastapi      >= 0.136,<0.137
uvicorn[standard] >= 0.30
# dev
pytest       >= 8.2
moto[s3,secretsmanager] >= 5.0
coverage     >= 7.5
ruff         >= 0.5
mypy         >= 1.10
boto3-stubs[s3,secretsmanager]
httpx        >= 0.27          # FastAPI TestClient
```

---

## 3. Repository layout

Each directory has exactly one responsibility (stated in the comment).

```
aws-wrapper/
├── pyproject.toml
├── uv.lock
├── README.md
├── .gitignore
├── .python-version                 # "3.12"
├── ruff.toml
├── src/
│   └── aws_wrapper/
│       ├── __init__.py
│       ├── py.typed
│       │
│       ├── core/                    # cross-cutting infra; depends on nothing internal except itself
│       │   ├── __init__.py
│       │   ├── config.py            # Settings (pydantic-settings)
│       │   ├── auth.py              # ClientFactory (session + client cache)
│       │   ├── service.py           # BaseService — shared base for all services
│       │   ├── errors.py            # exception hierarchy + translate_error()
│       │   └── logging.py           # configure_logging / get_logger
│       │
│       ├── services/                # one package per AWS service; framework-agnostic
│       │   ├── __init__.py
│       │   ├── secrets_manager/     # FULLY IMPLEMENTED reference service
│       │   │   ├── __init__.py      # re-exports service + models
│       │   │   ├── models.py
│       │   │   ├── service.py       # SecretsManagerService(BaseService)
│       │   │   └── exceptions.py
│       │   └── s3/                  # SCAFFOLD — pattern only
│       │       ├── __init__.py
│       │       ├── models.py
│       │       ├── service.py       # S3Service(BaseService)
│       │       ├── exceptions.py
│       │       └── EXTENDING.md     # how to add an operation
│       │
│       ├── api/                     # FastAPI adapter; depends on services/ + core/
│       │   ├── __init__.py
│       │   ├── main.py              # app, router mounting, exception->HTTP handlers
│       │   ├── deps.py              # Depends() providers
│       │   └── routers/
│       │       ├── __init__.py
│       │       ├── secrets_manager.py
│       │       └── s3.py
│       │
│       └── cli/                     # Typer adapter; depends on services/ + core/
│           ├── __init__.py
│           ├── main.py              # root Typer app, global options, exit handling
│           ├── context.py           # CliContext (settings, factory, output fmt)
│           ├── commands/
│           │   ├── __init__.py
│           │   ├── secrets_manager.py
│           │   └── s3.py
│           └── output/              # presentation layer — class-based formatters
│               ├── __init__.py      # registry + render() entry point
│               ├── base.py          # Formatter protocol
│               ├── json.py          # JsonFormatter
│               ├── table.py         # TableFormatter (Rich)
│               └── yaml.py          # YamlFormatter
│
└── tests/                           # mirrors src/ layout
    ├── __init__.py
    ├── conftest.py
    ├── unit/
    │   ├── test_core_config.py
    │   ├── test_core_auth.py
    │   ├── test_core_errors.py
    │   ├── test_base_service.py
    │   └── services/
    │       ├── test_secrets_manager.py
    │       └── test_s3.py
    ├── api/
    │   └── test_secrets_manager_routes.py
    └── cli/
        ├── test_output_formatters.py
        └── test_secrets_manager_commands.py
```

**Naming note:** the service implementation file is `service.py` inside each service package (e.g. `services/secrets_manager/service.py`), parallel to `models.py` and `exceptions.py`. This reads more intuitively than `client.py` since the class is a `*Service`, and avoids confusion with the boto3 "client" it wraps.

---

## 4. `core/`

### 4.1 `core/config.py`

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Reads env with prefix AWS_WRAPPER_.
    AWS-native vars (AWS_REGION, AWS_PROFILE, ...) are honored by boto3
    directly and need not be duplicated here."""

    model_config = SettingsConfigDict(
        env_prefix="AWS_WRAPPER_", env_file=".env", extra="ignore"
    )

    region: str | None = Field(default=None, description="AWS region override")
    profile: str | None = Field(default=None, description="AWS named profile")
    endpoint_url: str | None = Field(default=None, description="Endpoint override (tests/localstack)")
    max_retries: int = Field(default=3, ge=0)
    retry_mode: str = Field(default="standard")  # standard | adaptive | legacy
    log_level: str = Field(default="INFO")


def get_settings() -> Settings:
    return Settings()
```

No hardcoded default region (keeps GovCloud working).

### 4.2 `core/auth.py`

```python
import boto3
from botocore.config import Config as BotoConfig

from aws_wrapper.core.config import Settings


class ClientFactory:
    """Builds and caches boto3 clients from Settings. One per Settings instance."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._session = self._build_session()
        self._clients: dict[str, object] = {}

    def _build_session(self) -> boto3.Session:
        kwargs: dict[str, object] = {}
        if self._settings.profile:
            kwargs["profile_name"] = self._settings.profile
        if self._settings.region:
            kwargs["region_name"] = self._settings.region
        return boto3.Session(**kwargs)

    def _boto_config(self) -> BotoConfig:
        return BotoConfig(
            retries={"max_attempts": self._settings.max_retries, "mode": self._settings.retry_mode}
        )

    def client(self, service_name: str):
        if service_name not in self._clients:
            kwargs: dict[str, object] = {"config": self._boto_config()}
            if self._settings.endpoint_url:
                kwargs["endpoint_url"] = self._settings.endpoint_url
            self._clients[service_name] = self._session.client(service_name, **kwargs)
        return self._clients[service_name]
```

No `boto3.client(...)` anywhere else in the codebase.

### 4.3 `core/service.py` — BaseService

The shared base for every service. Stores the injected client; enforces that subclasses declare their boto3 service name.

```python
from aws_wrapper.core.auth import ClientFactory


class BaseService:
    """Base class for all AWS service wrappers.

    Subclasses MUST set the class attribute `service_name` to the boto3
    service identifier (e.g. 'secretsmanager', 's3'). The matching boto3
    client is resolved from the factory once at construction.
    """

    service_name: str  # subclasses must override

    def __init__(self, factory: ClientFactory) -> None:
        if not getattr(self, "service_name", None):
            raise NotImplementedError(
                f"{type(self).__name__} must define a `service_name` class attribute"
            )
        self._factory = factory
        self._client = factory.client(self.service_name)
```

Every service now omits its own `__init__` and just declares `service_name`.

### 4.4 `core/errors.py`

Exception hierarchy (classes) + a pure `translate_error` function. Unchanged in shape from v1:

```python
from botocore.exceptions import ClientError


class AwsWrapperError(Exception):
    """Base for all wrapper errors."""

class ResourceNotFoundError(AwsWrapperError): ...
class AccessDeniedError(AwsWrapperError): ...
class ConflictError(AwsWrapperError): ...
class ThrottledError(AwsWrapperError): ...
class ValidationError(AwsWrapperError): ...
class UpstreamError(AwsWrapperError):
    """Unclassified AWS-side error."""


_ERROR_CODE_MAP: dict[str, type[AwsWrapperError]] = {
    "ResourceNotFoundException": ResourceNotFoundError,
    "NoSuchKey": ResourceNotFoundError,
    "NoSuchBucket": ResourceNotFoundError,
    "404": ResourceNotFoundError,
    "AccessDeniedException": AccessDeniedError,
    "AccessDenied": AccessDeniedError,
    "ResourceExistsException": ConflictError,
    "BucketAlreadyExists": ConflictError,
    "BucketAlreadyOwnedByYou": ConflictError,
    "ThrottlingException": ThrottledError,
    "Throttling": ThrottledError,
    "TooManyRequestsException": ThrottledError,
    "ValidationException": ValidationError,
    "InvalidParameterException": ValidationError,
    "InvalidRequestException": ValidationError,
}


def translate_error(exc: ClientError) -> AwsWrapperError:
    """Convert a botocore ClientError into a domain exception.
    Usage: raise translate_error(e) from e"""
    err = exc.response.get("Error", {})
    cls = _ERROR_CODE_MAP.get(err.get("Code", ""), UpstreamError)
    return cls(err.get("Message", str(exc)))
```

### 4.5 `core/logging.py`

`configure_logging(settings)` + `get_logger(name)` using stdlib `logging`. No Rich here (Rich is a CLI presentation concern).

---

## 5. `services/secrets_manager/` — FULLY IMPLEMENTED reference

Operations: `get_secret_value`, `create_secret`, `put_secret_value`, `describe_secret`, `list_secrets` (paginated), `delete_secret`. All available in commercial + GovCloud (§11).

### 5.1 `models.py`

Pydantic v2; pure data + validators. `SecretStr` for sensitive values.

```python
from datetime import datetime
from pydantic import BaseModel, Field, SecretStr, model_validator


class GetSecretValueRequest(BaseModel):
    secret_id: str = Field(..., description="Secret name or ARN")
    version_id: str | None = None
    version_stage: str | None = None


class SecretValue(BaseModel):
    name: str
    arn: str
    version_id: str
    secret_string: SecretStr | None = None
    secret_binary: bytes | None = None
    created_date: datetime | None = None


class CreateSecretRequest(BaseModel):
    name: str
    secret_string: SecretStr | None = None
    secret_binary: bytes | None = None
    description: str | None = None
    kms_key_id: str | None = None
    tags: dict[str, str] | None = None

    @model_validator(mode="after")
    def _exactly_one_value(self):
        if (self.secret_string is None) == (self.secret_binary is None):
            raise ValueError("exactly one of secret_string or secret_binary is required")
        return self


class PutSecretValueRequest(BaseModel):
    secret_id: str
    secret_string: SecretStr | None = None
    secret_binary: bytes | None = None

    @model_validator(mode="after")
    def _exactly_one_value(self):
        if (self.secret_string is None) == (self.secret_binary is None):
            raise ValueError("exactly one of secret_string or secret_binary is required")
        return self


class SecretMetadata(BaseModel):
    name: str
    arn: str
    description: str | None = None
    kms_key_id: str | None = None
    rotation_enabled: bool = False
    last_changed_date: datetime | None = None
    last_accessed_date: datetime | None = None
    tags: dict[str, str] = Field(default_factory=dict)


class ListSecretsRequest(BaseModel):
    name_prefix: str | None = None
    max_results: int | None = Field(default=None, ge=1)


class CreateSecretResponse(BaseModel):
    name: str
    arn: str
    version_id: str


class DeleteSecretRequest(BaseModel):
    secret_id: str
    recovery_window_days: int | None = Field(default=None, ge=7, le=30)
    force_delete: bool = False

    @model_validator(mode="after")
    def _window_xor_force(self):
        if self.force_delete and self.recovery_window_days is not None:
            raise ValueError("recovery_window_days and force_delete are mutually exclusive")
        return self


class DeleteSecretResponse(BaseModel):
    name: str
    arn: str
    deletion_date: datetime | None = None
```

### 5.2 `service.py`

Inherits `BaseService`; declares `service_name`; no `__init__`.

```python
from botocore.exceptions import ClientError

from aws_wrapper.core.errors import translate_error
from aws_wrapper.core.service import BaseService
from aws_wrapper.services.secrets_manager.models import (
    CreateSecretRequest, CreateSecretResponse, DeleteSecretRequest,
    DeleteSecretResponse, GetSecretValueRequest, ListSecretsRequest,
    PutSecretValueRequest, SecretMetadata, SecretValue,
)


class SecretsManagerService(BaseService):
    service_name = "secretsmanager"

    def get_secret_value(self, req: GetSecretValueRequest) -> SecretValue:
        kwargs = {"SecretId": req.secret_id}
        if req.version_id:
            kwargs["VersionId"] = req.version_id
        if req.version_stage:
            kwargs["VersionStage"] = req.version_stage
        try:
            r = self._client.get_secret_value(**kwargs)
        except ClientError as e:
            raise translate_error(e) from e
        return SecretValue(
            name=r["Name"], arn=r["ARN"], version_id=r["VersionId"],
            secret_string=r.get("SecretString"), secret_binary=r.get("SecretBinary"),
            created_date=r.get("CreatedDate"),
        )

    def create_secret(self, req: CreateSecretRequest) -> CreateSecretResponse:
        kwargs: dict = {"Name": req.name}
        if req.secret_string is not None:
            kwargs["SecretString"] = req.secret_string.get_secret_value()
        if req.secret_binary is not None:
            kwargs["SecretBinary"] = req.secret_binary
        if req.description:
            kwargs["Description"] = req.description
        if req.kms_key_id:
            kwargs["KmsKeyId"] = req.kms_key_id
        if req.tags:
            kwargs["Tags"] = [{"Key": k, "Value": v} for k, v in req.tags.items()]
        try:
            r = self._client.create_secret(**kwargs)
        except ClientError as e:
            raise translate_error(e) from e
        return CreateSecretResponse(name=r["Name"], arn=r["ARN"], version_id=r["VersionId"])

    def put_secret_value(self, req: PutSecretValueRequest) -> CreateSecretResponse:
        kwargs: dict = {"SecretId": req.secret_id}
        if req.secret_string is not None:
            kwargs["SecretString"] = req.secret_string.get_secret_value()
        if req.secret_binary is not None:
            kwargs["SecretBinary"] = req.secret_binary
        try:
            r = self._client.put_secret_value(**kwargs)
        except ClientError as e:
            raise translate_error(e) from e
        return CreateSecretResponse(name=r["Name"], arn=r["ARN"], version_id=r["VersionId"])

    def describe_secret(self, secret_id: str) -> SecretMetadata:
        try:
            r = self._client.describe_secret(SecretId=secret_id)
        except ClientError as e:
            raise translate_error(e) from e
        return SecretMetadata(
            name=r["Name"], arn=r["ARN"], description=r.get("Description"),
            kms_key_id=r.get("KmsKeyId"), rotation_enabled=r.get("RotationEnabled", False),
            last_changed_date=r.get("LastChangedDate"), last_accessed_date=r.get("LastAccessedDate"),
            tags={t["Key"]: t["Value"] for t in r.get("Tags", [])},
        )

    def list_secrets(self, req: ListSecretsRequest) -> list[SecretMetadata]:
        paginator = self._client.get_paginator("list_secrets")
        paginate_kwargs: dict = {}
        if req.name_prefix:
            paginate_kwargs["Filters"] = [{"Key": "name", "Values": [req.name_prefix]}]
        out: list[SecretMetadata] = []
        try:
            for page in paginator.paginate(**paginate_kwargs):
                for s in page.get("SecretList", []):
                    out.append(SecretMetadata(
                        name=s["Name"], arn=s["ARN"], description=s.get("Description"),
                        kms_key_id=s.get("KmsKeyId"), rotation_enabled=s.get("RotationEnabled", False),
                        last_changed_date=s.get("LastChangedDate"),
                        last_accessed_date=s.get("LastAccessedDate"),
                        tags={t["Key"]: t["Value"] for t in s.get("Tags", [])},
                    ))
                    if req.max_results and len(out) >= req.max_results:
                        return out[: req.max_results]
        except ClientError as e:
            raise translate_error(e) from e
        return out

    def delete_secret(self, req: DeleteSecretRequest) -> DeleteSecretResponse:
        kwargs: dict = {"SecretId": req.secret_id}
        if req.force_delete:
            kwargs["ForceDeleteWithoutRecovery"] = True
        elif req.recovery_window_days is not None:
            kwargs["RecoveryWindowInDays"] = req.recovery_window_days
        try:
            r = self._client.delete_secret(**kwargs)
        except ClientError as e:
            raise translate_error(e) from e
        return DeleteSecretResponse(name=r["Name"], arn=r["ARN"], deletion_date=r.get("DeletionDate"))
```

### 5.3 `exceptions.py`

Minimal service-specific subclasses where they add clarity, e.g. `class SecretNotFoundError(ResourceNotFoundError): ...`. Most cases are covered by core translation.

### 5.4 `__init__.py`

Re-export `SecretsManagerService` and all public models.

---

## 6. `services/s3/` — SCAFFOLD

Implement `head_object` fully; stub the rest. Demonstrates the `BaseService` pattern.

`service.py`:

```python
from botocore.exceptions import ClientError

from aws_wrapper.core.errors import translate_error
from aws_wrapper.core.service import BaseService
from aws_wrapper.services.s3.models import HeadObjectRequest, HeadObjectResponse


class S3Service(BaseService):
    service_name = "s3"

    def head_object(self, req: HeadObjectRequest) -> HeadObjectResponse:
        kwargs = {"Bucket": req.bucket, "Key": req.key}
        if req.version_id:
            kwargs["VersionId"] = req.version_id
        try:
            r = self._client.head_object(**kwargs)
        except ClientError as e:
            raise translate_error(e) from e
        return HeadObjectResponse(
            content_length=r["ContentLength"], content_type=r.get("ContentType", ""),
            etag=r["ETag"], last_modified=r["LastModified"], metadata=r.get("Metadata", {}),
        )

    def list_objects(self, req):  # noqa: ANN001
        # TODO(extend): implement with paginator "list_objects_v2".
        # Pattern: see SecretsManagerService.list_secrets.
        raise NotImplementedError(
            "s3.list_objects not implemented — see SecretsManagerService.list_secrets"
        )

    def get_object(self, req):  # noqa: ANN001
        # TODO(extend): implement get_object; stream body or return bytes.
        raise NotImplementedError("s3.get_object not implemented")
```

`EXTENDING.md` — the 4-step checklist: add model → add `*Service` method (wrap `ClientError` with `translate_error`) → add router endpoint → add CLI command.

---

## 7. `api/` — FastAPI adapter (Option A)

### 7.1 `deps.py`

```python
from functools import lru_cache
from fastapi import Depends

from aws_wrapper.core.auth import ClientFactory
from aws_wrapper.core.config import Settings, get_settings
from aws_wrapper.services.secrets_manager import SecretsManagerService
from aws_wrapper.services.s3 import S3Service


@lru_cache
def _factory_for(settings: Settings) -> ClientFactory:
    return ClientFactory(settings)


def get_factory(settings: Settings = Depends(get_settings)) -> ClientFactory:
    return _factory_for(settings)


def get_secrets_manager_service(f: ClientFactory = Depends(get_factory)) -> SecretsManagerService:
    return SecretsManagerService(f)


def get_s3_service(f: ClientFactory = Depends(get_factory)) -> S3Service:
    return S3Service(f)
```

### 7.2 `routers/secrets_manager.py`

Thin; every sync call wrapped in `run_in_threadpool`. (Same as v1.)

```python
from fastapi import APIRouter, Depends, status
from fastapi.concurrency import run_in_threadpool

from aws_wrapper.api.deps import get_secrets_manager_service
from aws_wrapper.services.secrets_manager import (
    CreateSecretRequest, CreateSecretResponse, GetSecretValueRequest,
    SecretValue, SecretsManagerService,
)

router = APIRouter(prefix="/secrets-manager", tags=["secrets-manager"])


@router.post("/secrets:get-value", response_model=SecretValue)
async def get_secret_value(
    req: GetSecretValueRequest,
    svc: SecretsManagerService = Depends(get_secrets_manager_service),
) -> SecretValue:
    return await run_in_threadpool(svc.get_secret_value, req)


@router.post("/secrets", response_model=CreateSecretResponse, status_code=status.HTTP_201_CREATED)
async def create_secret(
    req: CreateSecretRequest,
    svc: SecretsManagerService = Depends(get_secrets_manager_service),
) -> CreateSecretResponse:
    return await run_in_threadpool(svc.create_secret, req)

# ... put-value, describe, list, delete
```

Secret values travel in POST bodies only (never path/query) so they stay out of access logs.

### 7.3 `main.py`

App, router mounting, and a single `AwsWrapperError -> HTTP` exception handler (the thing that keeps routers thin). Same as v1: 404/403/409/422/429 mapping, `502` fallback, `/healthz`.

---

## 8. `cli/` — Typer adapter

### 8.1 `context.py`

```python
from dataclasses import dataclass
from aws_wrapper.core.auth import ClientFactory
from aws_wrapper.core.config import Settings


@dataclass
class CliContext:
    settings: Settings
    factory: ClientFactory
    output: str  # "json" | "table" | "yaml"
```

### 8.2 `output/` — class-based formatter package

**`base.py`** — the protocol:

```python
from typing import Protocol, runtime_checkable
from pydantic import BaseModel


@runtime_checkable
class Formatter(Protocol):
    """Renders a Pydantic model or list of models to a string."""

    def render(self, data: BaseModel | list[BaseModel], *, show_secret: bool = False) -> str:
        ...
```

**`json.py`**:

```python
import json
from pydantic import BaseModel
from aws_wrapper.cli.output.base import Formatter


class JsonFormatter:
    def render(self, data, *, show_secret: bool = False) -> str:
        def dump(m: BaseModel) -> dict:
            # SecretStr serializes as '**********' unless explicitly revealed.
            ctx = {"show_secret": show_secret}
            return m.model_dump(mode="json", context=ctx)
        payload = [dump(m) for m in data] if isinstance(data, list) else dump(data)
        return json.dumps(payload, indent=2, default=str)
```

(Models that hold a `SecretStr` should implement a `field_serializer` that checks `info.context.get("show_secret")` and reveals only when true; otherwise emit `"***"`.)

**`table.py`** — Rich `Table`; one row per model, columns from model fields; secrets redacted unless `show_secret`.

**`yaml.py`** — `yaml.safe_dump` of the same dict structure as JSON.

**`__init__.py`** — registry + entry point:

```python
from pydantic import BaseModel
from aws_wrapper.cli.output.base import Formatter
from aws_wrapper.cli.output.json import JsonFormatter
from aws_wrapper.cli.output.table import TableFormatter
from aws_wrapper.cli.output.yaml import YamlFormatter

_REGISTRY: dict[str, Formatter] = {
    "json": JsonFormatter(),
    "table": TableFormatter(),
    "yaml": YamlFormatter(),
}


def render(data: BaseModel | list[BaseModel], fmt: str, *, show_secret: bool = False) -> str:
    try:
        formatter = _REGISTRY[fmt]
    except KeyError:
        raise ValueError(f"unknown output format: {fmt!r} (choose from {', '.join(_REGISTRY)})")
    return formatter.render(data, show_secret=show_secret)
```

Adding a format = new file + one registry line. Commands call `render(...)` and `typer.echo` the result — they never format directly.

### 8.3 `main.py`

Root Typer app, global `--output/--region/--profile`, builds `CliContext` in the callback, mounts sub-apps, and wraps execution so domain exceptions print a clean red message with a non-zero exit code (no traceback). (Same shape as v1.)

### 8.4 `commands/secrets_manager.py`

```python
import typer
from aws_wrapper.cli.context import CliContext
from aws_wrapper.cli.output import render
from aws_wrapper.services.secrets_manager import (
    GetSecretValueRequest, ListSecretsRequest, SecretsManagerService,
)

app = typer.Typer(help="Secrets Manager operations", no_args_is_help=True)


@app.command("get-value")
def get_value(
    ctx: typer.Context,
    secret_id: str = typer.Argument(..., help="Secret name or ARN"),
    version_id: str = typer.Option(None, "--version-id"),
    show_secret: bool = typer.Option(False, "--show-secret"),
) -> None:
    c: CliContext = ctx.obj
    svc = SecretsManagerService(c.factory)
    result = svc.get_secret_value(GetSecretValueRequest(secret_id=secret_id, version_id=version_id))
    typer.echo(render(result, c.output, show_secret=show_secret))


@app.command("list")
def list_secrets(
    ctx: typer.Context,
    name_prefix: str = typer.Option(None, "--prefix"),
    max_results: int = typer.Option(None, "--max"),
) -> None:
    c: CliContext = ctx.obj
    svc = SecretsManagerService(c.factory)
    results = svc.list_secrets(ListSecretsRequest(name_prefix=name_prefix, max_results=max_results))
    typer.echo(render(results, c.output))

# ... create, put-value, describe, delete
```

### 8.5 `commands/s3.py`

`head-object` implemented; rest stubbed with `raise typer.Exit(1)` + `# TODO(extend)`.

---

## 9. `pyproject.toml`

```toml
[project]
name = "aws-wrapper"
version = "0.1.0"
description = "Consolidated AWS service wrappers: library, CLI, and API."
requires-python = ">=3.11"
dependencies = [
    "boto3>=1.34",
    "botocore>=1.34",
    "pydantic>=2.7,<3",
    "pydantic-settings>=2.3,<3",
]

[project.optional-dependencies]
cli = ["typer>=0.12,<1", "rich>=13.7", "pyyaml>=6.0"]
api = ["fastapi>=0.136,<0.137", "uvicorn[standard]>=0.30"]
all = ["aws-wrapper[cli,api]"]

[project.scripts]
aws-wrapper = "aws_wrapper.cli.main:run"

[dependency-groups]
dev = [
    "pytest>=8.2",
    "moto[s3,secretsmanager]>=5.0",
    "coverage>=7.5",
    "ruff>=0.5",
    "mypy>=1.10",
    "boto3-stubs[s3,secretsmanager]",
    "httpx>=0.27",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/aws_wrapper"]

[tool.ruff]
line-length = 88
target-version = "py311"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "TCH", "ANN"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"

[tool.mypy]
python_version = "3.11"
strict = true
packages = ["aws_wrapper"]
```

---

## 10. Testing

- **`conftest.py`**: `settings` fixture (`region="us-east-1"`), `factory` fixture wrapped in moto's `mock_aws`, per-service fixtures.
- **`test_base_service.py`**: subclass without `service_name` raises `NotImplementedError`; a valid subclass resolves the right client.
- **Service tests** (`test_secrets_manager.py`): create→get→describe→list→put→delete round-trips under moto; missing secret raises `ResourceNotFoundError` (proves translation wiring); `list_secrets` paginates and respects `max_results`.
- **`test_output_formatters.py`**: each formatter renders a sample model; secrets are redacted unless `show_secret=True`; unknown format raises `ValueError`.
- **API tests**: `TestClient`; 201 on create, 404 mapped from `ResourceNotFoundError`, schema matches.
- **CLI tests**: Typer `CliRunner`; `get-value`/`list` exit 0 with parseable JSON; missing secret yields non-zero exit and clean error.
- Coverage target ≥85% on `core/` and `services/`.

---

## 11. Partition note (commercial vs GovCloud)

S3 and Secrets Manager — and the operations implemented here — exist in both AWS commercial and GovCloud. Because the wrapper never hardcodes region/partition and lets region flow from standard AWS config/env, **boto3 resolves GovCloud endpoints automatically when a `us-gov-*` region is supplied**; no special code is required. Forward guidance for the README: any later service that is commercial-only (or has GovCloud gaps) must document its availability in its module docstring/README. If FIPS-endpoint enforcement or partition-gated operations become a hard requirement, add `partition` / `use_fips_endpoint` to `Settings` and a guard in `core/auth.py` — but do not build it preemptively.

---

## 12. README content

Purpose paragraph; install (`uv sync`, extras); three usage modes (library import + factory, `aws-wrapper secrets-manager get-value ...`, `uvicorn aws_wrapper.api.main:app`); condensed architecture rules from §1; the 4-step "add a new service/operation" checklist; the partition note; Secrets Manager availability line (commercial + GovCloud).

---

## 13. Build order

1. `uv init`; `pyproject.toml`, `.python-version`, `ruff.toml`, `.gitignore`; `uv sync`.
2. `core/`: `config.py` → `errors.py` → `logging.py` → `auth.py` → `service.py` (BaseService). Tests alongside (`test_core_*`, `test_base_service.py`).
3. `services/secrets_manager/` fully (models → exceptions → service → `__init__`). `test_secrets_manager.py` green under moto.
4. `cli/`: `context.py` → `output/` package (base → json → table → yaml → `__init__`) → `main.py` → `commands/secrets_manager.py`. `test_output_formatters.py` + CLI tests.
5. `api/`: `deps.py` → `routers/secrets_manager.py` → `main.py`. API tests.
6. `services/s3/` scaffold (`head_object` real, rest stubbed) + `routers/s3.py` + `commands/s3.py` mirroring; `EXTENDING.md`.
7. README. Final `uv run ruff check`, `ruff format`, `mypy`, `pytest --cov` — all green.

**Definition of done:** `uv run pytest` passes, `ruff check` and `mypy` clean, `aws-wrapper --help` and `uvicorn aws_wrapper.api.main:app` both start, and a developer can add a new S3 operation following only `EXTENDING.md`.
