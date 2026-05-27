# Architecture

This document explains **how cloud-relay is shaped at runtime** — the
layering rules, where state lives, what happens during a request, and where
to look when you need to extend something. For the original *build spec*
(top-down "create these files in this order") see [AWS_WRAPPER_SPEC_v2.md](AWS_WRAPPER_SPEC_v2.md).
For the issues that surfaced during the initial build, see
[VALIDATION_FINDINGS.md](VALIDATION_FINDINGS.md).

## 1. The shape

cloud-relay is a **diamond**: one cloud-neutral core, one provider layer,
two thin adapters that depend on the provider but never on each other.

```
            ┌──────────┐         ┌──────────┐
            │   CLI    │         │   API    │     ← thin adapters
            │  (Typer) │         │ (FastAPI)│
            └─────┬────┘         └─────┬────┘
                  └────────┬───────────┘
                           ▼
                    ┌─────────────┐
                    │  services/  │     ← per-cloud service wrappers
                    │  aws/  ...  │       (boto3 today; gcp/azure later)
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │    core/    │     ← cloud-neutral primitives:
                    │             │       Settings, errors, logging
                    └─────────────┘
```

Three rules keep this enforceable:

1. **`core/` imports no cloud SDK.** Not boto3, not google-cloud, not
   azure-sdk. Grep proves it. This is what makes adding a cloud purely
   additive.
2. **Services never import adapters.** Code under `services/` MUST NOT
   import FastAPI, Typer, or Rich. They're reusable from scripts, notebooks,
   Lambda, anywhere.
3. **CLI and API never import each other.** They are peers; both depend on
   `services/` and `core/`.

## 2. Where things live

| Concern | Location |
|---|---|
| Log level, base settings, generic exceptions | [`core/`](../src/cloud_relay/core/) |
| AWS-specific settings, factory, base class, error translation | [`services/aws/_core/`](../src/cloud_relay/services/aws/_core/) |
| One AWS service wrapper | [`services/aws/<svc>/`](../src/cloud_relay/services/aws/) |
| HTTP routes for an AWS service | [`api/routers/aws/<svc>.py`](../src/cloud_relay/api/routers/aws/) |
| CLI commands for an AWS service | [`cli/commands/aws/<svc>.py`](../src/cloud_relay/cli/commands/aws/) |
| Output formatters (JSON/table/YAML) | [`cli/output/`](../src/cloud_relay/cli/output/) |

The `_core` underscore signals it's private to the provider package. Other
code reaches in for `ClientFactory`, `BaseService`, `AwsSettings`,
`translate_error` and nothing else.

## 3. Provider model (the multi-cloud hook)

Adding GCP later is purely additive:

```
services/
├── aws/
│   ├── _core/        # AwsSettings, boto3 ClientFactory, AWS BaseService,
│   │                 #   translate_error(botocore.ClientError)
│   ├── secrets_manager/
│   └── s3/
└── gcp/                          ← future
    ├── _core/                    # GcpSettings(Settings), google.cloud
    │                             #   factory, GcpBaseService, translate_error
    │                             #   for google.api_core exceptions
    └── secret_manager/
```

Both providers' settings inherit from `core.config.Settings` so the
cloud-neutral `log_level` is shared. Each provider's `_core/errors.py` maps
its own SDK exceptions onto the same `CloudRelayError` hierarchy in `core/`
— so adapters keep catching `ResourceNotFoundError` without caring which
cloud produced it.

## 4. State

**There is none in `services/`.** Every call hits the cloud SDK fresh.
Three consequences:

- The wrapper is safe to scale horizontally (Lambda, Fargate, K8s pods —
  any process can serve any request).
- Tests don't need a database or migrations; moto in-memory + a fresh
  `ClientFactory` per test is enough.
- Caching is an *out-of-scope concern*: if a caller needs it, they wrap
  the service externally (e.g. a `CachingS3Service` decorator), not by
  smuggling state into `S3Service`.

The one piece of process-local state is the **boto3 client cache** inside
`ClientFactory` — one client per AWS service per process. That's an
efficiency optimization (a boto3 client is expensive to construct), not
business state. It's invisible to callers and rebuilt on `reset_factory_cache()`
during tests.

## 5. Configuration flow

```
            ┌────────────────────────────────┐
   env ───► │ CLOUD_RELAY_* / AWS_*          │
            │  ├─ CLOUD_RELAY_LOG_LEVEL  ──► core.config.Settings
            │  ├─ CLOUD_RELAY_REGION     ──► services.aws._core.config.AwsSettings
            │  ├─ CLOUD_RELAY_PROFILE    ──► AwsSettings
            │  ├─ CLOUD_RELAY_ENDPOINT_URL── AwsSettings  (tests/localstack)
            │  └─ AWS_*                  ──► boto3 (native; not duplicated)
            └────────────────────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ ClientFactory   │  builds boto3.Session(profile, region),
                   │                 │  caches one client per service
                   └─────────────────┘
                            │
                            ▼
                   *Service(factory)   ← BaseService stores _client
```

Settings are read **once per process** on first use. The CLI builds them
in its root callback ([cli/main.py:34](../src/cloud_relay/cli/main.py#L34));
the API builds them lazily on first request via `@lru_cache`
([api/deps.py:18-28](../src/cloud_relay/api/deps.py#L18-L28)).

CLI overrides (`--region`, `--profile`) are passed at `AwsSettings`
construction so Pydantic validators run — the model is never mutated
after creation.

## 6. Lifecycle of a single call

Take `cloud-relay aws secrets-manager get-value db/password`:

1. **Typer parses argv.** Builds a `CliContext` on `ctx.obj` (settings,
   AWS factory, output format). Calls
   [cli/commands/aws/secrets_manager.py:get_value()](../src/cloud_relay/cli/commands/aws/secrets_manager.py).
2. **Command constructs the service.** `SecretsManagerService(c.aws_factory)`.
   The `BaseService.__init__` resolves the boto3 `secretsmanager` client
   from the factory (cached) and stores it as `self._client`.
3. **Command calls one service method.** `svc.get_secret_value(req)` where
   `req` is a `GetSecretValueRequest` Pydantic model.
4. **Service does the work.** Builds boto3 kwargs from the request model,
   calls `self._client.get_secret_value(...)` inside `try/except ClientError`.
   On failure: `raise translate_error(e) from e` — botocore exception →
   one of `ResourceNotFoundError`, `AccessDeniedError`, etc.
5. **Service returns a Pydantic model.** `SecretValue(...)`. boto3's raw
   dict never escapes the service layer.
6. **Command renders.** `render(result, c.output, show_secret=False)` picks
   a formatter from the registry. Secret fields are masked at the *model*
   layer (via `field_serializer`), not the formatter, so all three formats
   inherit the masking.
7. **`typer.echo` prints.** If any `CloudRelayError` propagated out, the
   `run()` wrapper in [cli/main.py:51-55](../src/cloud_relay/cli/main.py#L51-L55)
   prints a red one-liner and exits non-zero. No traceback.

The HTTP equivalent (`POST /aws/secrets-manager/secrets:get-value`) is the
same except:

- Step 1 is FastAPI body parsing → `Depends(get_secrets_manager_service)`.
- Step 3 is wrapped in `run_in_threadpool` so the event loop stays free
  (boto3 is blocking; we don't pretend otherwise).
- Step 7 is the global exception handler in
  [api/main.py:50-58](../src/cloud_relay/api/main.py#L50-L58) mapping
  domain exceptions to 404/403/409/422/429 with a 502 fallback.

## 7. Error model

Every operation either returns a typed model or raises one of these:

| Domain exception | Triggered by | HTTP code |
|---|---|---|
| `ResourceNotFoundError` | `ResourceNotFoundException`, `NoSuchKey`, `NoSuchBucket`, `404` | 404 |
| `AccessDeniedError` | `AccessDeniedException`, `AccessDenied` | 403 |
| `ConflictError` | `ResourceExistsException`, `BucketAlreadyExists`, … | 409 |
| `ValidationError` | `ValidationException`, `InvalidParameterException` | 422 |
| `ThrottledError` | `ThrottlingException`, `Throttling`, `TooManyRequestsException` | 429 |
| `UpstreamError` | anything unmapped | 502 |

The map lives in [aws/_core/errors.py](../src/cloud_relay/services/aws/_core/errors.py).
Extending it = adding one line per new error code. Adapters never look at
boto3 codes directly — they only catch the domain types.

## 8. The output layer (CLI-only)

`render(data, fmt, show_secret=...)` is the single entry point. It picks a
`Formatter` from a small registry:

```
data (Pydantic) ─► JsonFormatter / TableFormatter / YamlFormatter ─► str
                                  ▲
                                  │
                              registry in cli/output/__init__.py
```

Adding a new format = a new module with a class that satisfies the
`Formatter` protocol, plus one line in the registry. Commands call
`render()` and never format or print directly.

Secret masking happens at the **model** layer via Pydantic's
`field_serializer` (see [models.py:_reveal_if_requested](../src/cloud_relay/services/aws/secrets_manager/models.py#L41-L53)).
Formatters pass `context={"show_secret": True}` through `model_dump`.
This means **all three formats inherit masking for free** — and adding a
fourth gets it free too.

## 9. Why these choices

For the full rationale see the spec (§1 "Guiding principles"). The
high-bit summary:

- **Sync boto3, sync services, sync CLI; API wraps sync in
  `run_in_threadpool`.** boto3 is blocking. Pretending otherwise (aioboto3,
  threading inside services) adds complexity without measurable benefit
  for the kinds of calls we make. The threadpool keeps the event loop free
  for *other* requests without infecting the service layer.
- **Classes where state lives; functions where the transformation is pure.**
  Services, factory, settings, formatters, exceptions are classes. `translate_error`
  is a function. No frameworks-of-one-thing.
- **Shared Pydantic models in `services/<svc>/models.py`** used by both
  adapters. Changing a field updates the FastAPI schema, the CLI JSON
  output, and the library API in one place.
- **One client factory.** Single auditable place for credential and region
  resolution — and the only point in the codebase that calls
  `boto3.client(...)`.

## 10. Where to look for what

| When you need to… | Look at… |
|---|---|
| Add a new operation to an existing service | [services/aws/s3/EXTENDING.md](../src/cloud_relay/services/aws/s3/EXTENDING.md) |
| Add a new AWS service | mirror `services/aws/secrets_manager/` (4 files) |
| Add a new cloud (GCP/Azure) | create `services/<cloud>/_core/{config,auth,service,errors}.py` |
| Change how errors map to HTTP | [`api/main.py:_STATUS`](../src/cloud_relay/api/main.py#L37) |
| Change how a botocore code maps to a domain exception | [`aws/_core/errors.py:_ERROR_CODE_MAP`](../src/cloud_relay/services/aws/_core/errors.py) |
| Add a new CLI output format | `cli/output/<name>.py` + registry line |
| Tune retries / endpoint / region | `AwsSettings` (env vars or constructor) |
| Mask a new secret-ish field | `field_serializer` on the model, same pattern as `SecretValue.secret_string` |
