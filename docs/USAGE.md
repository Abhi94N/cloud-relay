# Usage

A deeper guide than the README's quickstart. Covers the three modes
(library, CLI, API), the full configuration surface, AWS authentication
options (including SSO and GovCloud), and operational guidance.

## 1. Three ways to use it

cloud-relay ships a **library** as the primary surface, plus two thin
adapters: a **CLI** and an **HTTP API**. Pick based on caller:

| Caller | Use |
|---|---|
| Other Python service / script / notebook | Library |
| Human operator / debugging / shell pipelines | CLI |
| Non-Python service, browser, or "AWS access behind a service boundary" | API |

All three call the same service objects underneath; behavior is identical.

## 2. Library

### 2.1 Minimal example

```python
from cloud_relay.services.aws._core import AwsSettings, ClientFactory
from cloud_relay.services.aws.secrets_manager import (
    SecretsManagerService, GetSecretValueRequest,
)

factory = ClientFactory(AwsSettings())           # region from AWS env/config
svc = SecretsManagerService(factory)
secret = svc.get_secret_value(GetSecretValueRequest(secret_id="db/password"))
print(secret.secret_string.get_secret_value())
```

### 2.2 Reusing the factory

A `ClientFactory` builds one boto3 session and caches one client per
service. **Build it once per process** and pass it to as many service
objects as you need:

```python
factory = ClientFactory(AwsSettings(region="us-east-1"))
secrets = SecretsManagerService(factory)
s3 = S3Service(factory)
# secrets and s3 share the same boto3 session
```

### 2.3 Multi-account / multi-region

Two factories, two settings:

```python
prod = ClientFactory(AwsSettings(profile="prod", region="us-east-1"))
gov  = ClientFactory(AwsSettings(profile="gov-account", region="us-gov-west-1"))
prod_secrets = SecretsManagerService(prod)
gov_secrets  = SecretsManagerService(gov)
```

There's no global state; factories are independent.

### 2.4 Error handling

Every service method raises one of the domain exceptions from
`cloud_relay.core.errors`. Catch the type, not the message:

```python
from cloud_relay.core.errors import (
    ResourceNotFoundError, AccessDeniedError, CloudRelayError,
)

try:
    secret = svc.get_secret_value(GetSecretValueRequest(secret_id="maybe"))
except ResourceNotFoundError:
    secret = None
except AccessDeniedError:
    raise   # let it propagate to your caller
except CloudRelayError as e:
    log.warning("unexpected wrapper error: %s", e)
    raise
```

The raw `botocore.ClientError` never escapes the service layer.

### 2.5 Secret handling

`SecretValue.secret_string` is a `pydantic.SecretStr`. It renders as
`'**********'` in reprs and logs. Call `.get_secret_value()` to access the
raw string:

```python
sv = svc.get_secret_value(GetSecretValueRequest(secret_id="db/password"))
print(sv)                                    # '...secret_string=SecretStr('**********')...'
print(sv.secret_string.get_secret_value())   # the real value
```

JSON/YAML output masks by default; reveal with the serialization context:

```python
sv.model_dump(mode="json", context={"show_secret": True})
```

## 3. CLI

### 3.1 Command tree

```
cloud-relay
├── aws
│   ├── secrets-manager
│   │   ├── get-value <id> [--version-id ID] [--show-secret]
│   │   ├── create <name> --value VAL [--description TEXT]
│   │   ├── put-value <id> --value VAL
│   │   ├── describe <id>
│   │   ├── list [--prefix STR] [--max N]
│   │   └── delete <id> [--force | --recovery-days N]
│   └── s3
│       ├── head-object <bucket> <key> [--version-id ID]
│       └── list-objects                       (stub — see EXTENDING.md)
```

Global options apply to every command and go *before* the subcommand:

```
cloud-relay --output json|table|yaml --region <r> --profile <p> <subcommand> ...
```

### 3.2 Examples

```bash
# Default JSON output
cloud-relay aws secrets-manager get-value db/password
cloud-relay aws secrets-manager get-value db/password --show-secret

# Table output (Rich-rendered)
cloud-relay --output table aws secrets-manager list --prefix app/

# YAML output, profile + region overrides
cloud-relay --output yaml --profile dev --region us-west-2 \
    aws secrets-manager describe app/api-key

# Create and put
cloud-relay aws secrets-manager create app/token --value "$(cat token.txt)"
cloud-relay aws secrets-manager put-value app/token --value "$(cat token-v2.txt)"

# Delete with recovery window
cloud-relay aws secrets-manager delete app/token --recovery-days 7
cloud-relay aws secrets-manager delete app/token --force      # immediate

# S3
cloud-relay aws s3 head-object my-bucket path/to/object.txt
```

### 3.3 Exit codes

| Code | Meaning |
|---|---|
| 0 | success |
| 1 | any `CloudRelayError` (printed in red on stderr, no traceback) |
| 2 | Typer / argparse usage error |

Pipe-friendly: `stdout` carries only the rendered output; errors go to
`stderr`.

## 4. API

### 4.1 Running it

```bash
uvicorn cloud_relay.api.main:app --reload                # dev
uvicorn cloud_relay.api.main:app --host 0.0.0.0 --port 8080 --workers 4   # prod
```

Interactive docs at `http://localhost:8000/docs` (Swagger) and
`http://localhost:8000/redoc` (ReDoc). The OpenAPI schema is at
`/openapi.json` and is generated from the same Pydantic models the
library and CLI use.

### 4.2 Routes

All AWS routes are prefixed `/aws/<service>/...`:

| Method | Path | Notes |
|---|---|---|
| `GET`  | `/healthz` | Liveness probe |
| `POST` | `/aws/secrets-manager/secrets` | Create secret. **201** on success |
| `POST` | `/aws/secrets-manager/secrets:get-value` | Fetch value (masked unless caller reveals) |
| `PUT`  | `/aws/secrets-manager/secrets:put-value` | New version of existing value |
| `GET`  | `/aws/secrets-manager/secrets/{secret_id}` | Metadata only (no value) |
| `POST` | `/aws/secrets-manager/secrets:list` | Optionally filtered by `name_prefix` |
| `POST` | `/aws/secrets-manager/secrets:delete` | With recovery window or force |
| `POST` | `/aws/s3/objects:head` | `HeadObject` metadata |

Secret values travel in **POST bodies only** (never path/query) so they
stay out of access logs.

### 4.3 Example with `curl`

```bash
curl -X POST http://localhost:8000/aws/secrets-manager/secrets:get-value \
  -H 'content-type: application/json' \
  -d '{"secret_id": "db/password"}'

# {"name": "db/password", "arn": "...", "version_id": "...",
#  "secret_string": "***", "secret_binary": null, "created_date": "..."}
```

### 4.4 Error mapping

| Domain exception | HTTP code | Body |
|---|---|---|
| `ResourceNotFoundError` | 404 | `{"error": "ResourceNotFoundError", "detail": "..."}` |
| `AccessDeniedError` | 403 | same shape |
| `ConflictError` | 409 | same shape |
| `ValidationError` | 422 | same shape |
| `ThrottledError` | 429 | same shape |
| anything unmapped | 502 | same shape, `error: "UpstreamError"` |

Validation errors raised by Pydantic at request-parse time produce
FastAPI's standard 422 body (a list of field errors).

## 5. Configuration reference

cloud-relay honors **two** env-var families. They compose:

- `CLOUD_RELAY_*` — cloud-relay's own settings.
- `AWS_*` — standard AWS variables read by boto3 directly. cloud-relay
  does not duplicate these; boto3 picks them up natively.

### 5.1 cloud-relay vars (all optional)

| Var | Default | Notes |
|---|---|---|
| `CLOUD_RELAY_LOG_LEVEL` | `INFO` | Root log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `CLOUD_RELAY_REGION` | unset | AWS region override. Use `us-gov-*` for GovCloud |
| `CLOUD_RELAY_PROFILE` | unset | Named AWS profile from `~/.aws/credentials` |
| `CLOUD_RELAY_ENDPOINT_URL` | unset | Endpoint override (localstack, tests, vpce) |
| `CLOUD_RELAY_MAX_RETRIES` | `3` | botocore retry attempts |
| `CLOUD_RELAY_RETRY_MODE` | `standard` | `standard`, `adaptive`, or `legacy` |

Precedence (highest first): constructor args → env vars → `.env` file →
defaults. CLI `--region` / `--profile` are passed at construction so they
beat env.

### 5.2 AWS-native vars (read by boto3, listed for awareness)

`AWS_REGION`, `AWS_DEFAULT_REGION`, `AWS_PROFILE`, `AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, `AWS_CONFIG_FILE`,
`AWS_SHARED_CREDENTIALS_FILE`, `AWS_DEFAULT_PROFILE`, …

If you set both `CLOUD_RELAY_REGION` and `AWS_REGION`, the cloud-relay
one wins (because cloud-relay passes it explicitly to `boto3.Session`).

## 6. AWS authentication

cloud-relay does not manage credentials. It hands the `profile_name` (if
any) to `boto3.Session`, which uses the standard boto3 credential
resolution chain:

1. Constructor args (we don't use)
2. `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN`
3. `AWS_PROFILE` / explicit `profile_name`
4. EC2 instance profile / ECS task role / EKS IRSA
5. CLI cached SSO token (`~/.aws/sso/cache/`)
6. `~/.aws/credentials`

Three common patterns:

### 6.1 Static keys (dev / CI)

```bash
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_REGION=us-east-1
cloud-relay aws secrets-manager list
```

### 6.2 AWS SSO / IAM Identity Center (recommended for humans)

1. Configure `~/.aws/config`:
   ```ini
   [sso-session my-org]
   sso_start_url = https://my-org.awsapps.com/start
   sso_region = us-east-1
   sso_registration_scopes = sso:account:access

   [profile dev]
   sso_session = my-org
   sso_account_id = 123456789012
   sso_role_name = DeveloperAccess
   region = us-east-1
   ```
2. Log in once per session (opens browser, caches token for ~8h):
   ```bash
   aws sso login --profile dev
   ```
3. Use the profile:
   ```bash
   cloud-relay --profile dev aws secrets-manager list
   # or
   AWS_PROFILE=dev cloud-relay aws secrets-manager list
   ```

When the token expires you'll get a 502 / `UpstreamError` with the boto3
`UnauthorizedSSOTokenError` message. Re-run `aws sso login --profile dev`.

### 6.3 Instance / task role (recommended for production)

Don't set anything. Run cloud-relay on an EC2 instance with an instance
profile attached, or in an ECS task with a task role, or in a K8s pod
with IRSA. boto3 finds the metadata endpoint, mints short-lived
credentials, auto-refreshes. cloud-relay never touches credentials.

## 7. AWS commercial vs GovCloud

The implemented operations (Secrets Manager: all six; S3: `head_object`)
are available in **both partitions**. cloud-relay never hardcodes a
region or partition; passing a `us-gov-*` region routes boto3 to GovCloud
endpoints automatically.

```bash
CLOUD_RELAY_REGION=us-gov-west-1 cloud-relay aws secrets-manager list
# or
cloud-relay --region us-gov-west-1 aws secrets-manager list
```

Any service added later that is commercial-only, or has GovCloud gaps,
**must** document its availability in the service's module docstring and
in the top-level README.

## 8. Local development against localstack / moto

Point at any S3-compatible endpoint with `CLOUD_RELAY_ENDPOINT_URL`:

```bash
docker run -d -p 4566:4566 localstack/localstack
export CLOUD_RELAY_ENDPOINT_URL=http://localhost:4566
export CLOUD_RELAY_REGION=us-east-1
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
cloud-relay aws s3 head-object my-bucket some-key
```

Tests use [`moto`](https://docs.getmoto.org/) in-memory, not localstack;
they need no env vars beyond the region set in `tests/conftest.py`.

## 9. Production operational notes

- **Run sync workers.** boto3 is blocking; we wrap it in `run_in_threadpool`
  in the API so the event loop stays free. With `uvicorn`, pick a worker
  count based on your concurrency target — `--workers N` runs N
  processes; each process handles many requests via the threadpool.
- **Logging.** `CLOUD_RELAY_LOG_LEVEL` is honored at startup. Set
  `WARNING` or higher in prod unless debugging. The library uses stdlib
  `logging` only; route it however your platform expects.
- **No retries in the wrapper beyond boto3's own.** botocore's standard
  mode retries throttles and 5xxs with backoff; tune via
  `CLOUD_RELAY_MAX_RETRIES` and `CLOUD_RELAY_RETRY_MODE`.
- **Healthz.** The API exposes `GET /healthz` for liveness; it does not
  call AWS. Add your own readiness check if you need AWS reachability
  to gate traffic.
- **Secrets in logs.** `SecretStr` masks at the model layer. As long as
  you don't print the raw `SecretValue.secret_string.get_secret_value()`
  yourself, secret values won't end up in stdout/stderr/access logs.
