# cloud-relay

Consolidated cloud service wrappers for ground software. **cloud-relay is
primarily a library** of framework-agnostic service modules, with two thin
adapters layered on top: a **Typer CLI** for operators and debugging, and a
**FastAPI** HTTP API for non-Python consumers or when cloud access should sit
behind a service boundary.

Currently wraps **AWS Secrets Manager** (fully implemented) and **AWS S3**
(scaffold: `head-object` implemented, other operations stubbed for easy
extension). The package layout reserves room for additional providers
(`services/gcp/`, `services/azure/`, ...) behind the same shape; `core/` is
intentionally provider-agnostic so adding a cloud is purely additive.

## Architecture

```
src/cloud_relay/
├── core/                              # cloud-neutral cross-cutting infra:
│   ├── config.py                      #   Settings (log_level only)
│   ├── errors.py                      #   CloudRelayError hierarchy
│   └── logging.py
│
├── services/
│   └── aws/                           # ← everything AWS lives here
│       ├── _core/                     #   AWS-specific shared machinery:
│       │   ├── config.py              #     AwsSettings (region, profile, retries)
│       │   ├── auth.py                #     ClientFactory (only boto3.client call site)
│       │   ├── service.py             #     BaseService for AWS *Service classes
│       │   └── errors.py              #     translate_error(ClientError)
│       ├── secrets_manager/           #   one folder per service
│       └── s3/
│   (future: services/gcp/, services/azure/, services/oci/)
│
├── api/
│   ├── main.py                        # FastAPI app + lifespan (logging) +
│   │                                  #   domain→HTTP exception handler
│   ├── deps.py                        # per-provider Depends() providers
│   └── routers/
│       └── aws/                       # routes mounted at /aws/...
│           ├── secrets_manager.py
│           └── s3.py
│
└── cli/
    ├── main.py                        # root Typer app, mounts `aws` sub-app
    ├── context.py                     # CliContext (settings, aws_factory, output)
    ├── commands/
    │   └── aws/                       # cloud-relay aws ...
    │       ├── secrets_manager.py
    │       └── s3.py
    └── output/                        # JSON / table / YAML formatter registry
```

Load-bearing rules:

- **Services never import FastAPI, Typer, or Rich.** They depend only on their
  cloud SDK, Pydantic, and `core/`. This keeps them reusable from the library,
  API, CLI, notebooks, or scripts.
- **`core/` is provider-agnostic.** Nothing in `core/` imports boto3,
  google-cloud, azure-sdk, or any cloud SDK. Per-cloud machinery lives under
  `services/<cloud>/_core/`.
- **Adapters are thin.** Routers and CLI commands parse input, call one
  service method, and format output. No SDK calls, no business logic, no
  error-to-HTTP translation in the adapters.
- **CLI and API are peers.** Neither imports the other; both depend on
  `services/` and `core/`.
- **One client factory per cloud.** `services/aws/_core/auth.ClientFactory` is
  the only place boto3 clients are created; everything else receives an
  injected client.
- **Shared Pydantic models.** Request/response models live in
  `services/<cloud>/<svc>/models.py` and are used by both adapters.
- **Sync throughout.** Cloud SDKs are synchronous; the library and CLI are
  sync, and the API wraps service calls in `run_in_threadpool` so the event
  loop is never blocked.

## Prerequisites

- **Python 3.11+** (the repo pins 3.12 via `.python-version`).
- **uv** for environment and dependency management. Install with:
  - macOS / Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Windows (PowerShell): `irm https://astral.sh/uv/install.ps1 | iex`
  - Or `pipx install uv`.
- AWS credentials in the standard places (`~/.aws/credentials`, env vars, or
  instance/IRSA role) for any real AWS calls. Tests use moto and need none.

## Install

```bash
uv sync --all-extras          # everything, including dev tooling
uv sync --extra cli           # library + CLI only
uv sync --extra api           # library + API only
uv sync                       # library only (no FastAPI/Typer pulled in)
```

Copy `.env.example` to `.env` for local overrides; uncomment what you need.

## Usage

### As a library

```python
from cloud_relay.services.aws._core import AwsSettings, ClientFactory
from cloud_relay.services.aws.secrets_manager import (
    SecretsManagerService, GetSecretValueRequest,
)

factory = ClientFactory(AwsSettings())          # region from AWS env/config
svc = SecretsManagerService(factory)
secret = svc.get_secret_value(GetSecretValueRequest(secret_id="db/password"))
print(secret.secret_string.get_secret_value())
```

### As a CLI

Commands are namespaced by cloud provider:

```bash
cloud-relay aws secrets-manager list --prefix app/
cloud-relay aws secrets-manager get-value db/password --show-secret
cloud-relay --output table aws secrets-manager describe db/password
cloud-relay aws s3 head-object my-bucket path/to/object.txt
```

Global options: `--output json|table|yaml` (default `json`), `--region`,
`--profile`. Secret values are masked in output unless `--show-secret` is
passed.

### As an API

```bash
uvicorn cloud_relay.api.main:app --reload
```

```bash
curl -X POST localhost:8000/aws/secrets-manager/secrets:get-value \
  -H 'content-type: application/json' \
  -d '{"secret_id": "db/password"}'
```

Routes are namespaced by provider (`/aws/...`). Interactive docs at
`http://localhost:8000/docs`. Secret values are sent in request bodies (never
path/query) so they stay out of access logs.

## Documentation

The README is the quickstart. Deeper docs live in [`docs/`](docs/):

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — runtime model, layering
  rules, request lifecycle, error model, where to look to extend things.
- **[docs/USAGE.md](docs/USAGE.md)** — full CLI command tree, every config
  env var, AWS SSO setup, GovCloud, library patterns, API endpoint reference,
  production operational notes.
- **[docs/PACKAGING.md](docs/PACKAGING.md)** — local builds, wheel/sdist,
  single-file CLI binary (PyInstaller / shiv), GitLab Package Registry,
  PyPI.
- **[docs/AWS_WRAPPER_SPEC_v2.md](docs/AWS_WRAPPER_SPEC_v2.md)** — the
  original build spec (historical).
- **[docs/VALIDATION_FINDINGS.md](docs/VALIDATION_FINDINGS.md)** — issues
  the initial build surfaced; all folded into the implementation.

A CI pipeline is provided in [`.gitlab-ci.yml`](.gitlab-ci.yml) but
**fully commented out by default** — uncomment when ready.

## Adding things

- **A new operation to an existing service:** see
  [`src/cloud_relay/services/aws/s3/EXTENDING.md`](src/cloud_relay/services/aws/s3/EXTENDING.md)
  for the four-step process (model → service method → router → CLI command).
- **A new AWS service:** create `services/aws/<service>/{models,service,exceptions,__init__}.py`
  using the secrets_manager package as a template; then add a router under
  `api/routers/aws/` and a command module under `cli/commands/aws/`.
- **A new cloud provider:** create `services/<cloud>/_core/{config,auth,service,errors}.py`
  first — that gives the new package its own settings (inheriting from
  `core.config.Settings`), client factory, base class, and SDK-to-domain
  error translator. Then add services under it, mount routers at `/<cloud>/...`,
  and add a `cli/commands/<cloud>/` sub-app to the root Typer.

## AWS commercial vs GovCloud

The AWS-implemented operations are available in both AWS commercial and AWS
GovCloud. cloud-relay never hardcodes a region or partition; region flows from
standard AWS config/environment, so boto3 resolves GovCloud endpoints
automatically when a `us-gov-*` region is supplied. No special configuration
is required.

Any service added later that is commercial-only, or has GovCloud feature
gaps, **must** document its availability in its module docstring and here.

## Development

```bash
uv run ruff check . && uv run ruff format --check .   # lint + format
uv run mypy                                            # strict type checking
uv run pytest                                          # tests (moto-mocked AWS)
```

All AWS interactions in tests are mocked with `moto`; no credentials or
network access are required. The library, CLI, and API are pure Python with
no platform-specific code, so the workflow above works identically on Linux,
macOS, and Windows.
