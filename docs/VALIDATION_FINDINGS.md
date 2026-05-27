# cloud-relay — Validation Findings

The v2 spec was built end-to-end and run through `ruff`, `mypy --strict`, and
`pytest` (moto-mocked). **Final state: ruff clean, mypy strict clean across 33
files, 32 tests passing, 88% coverage** (core/ and services/ at 90–100%). The
CLI binary and the FastAPI app both boot and expose all routes.

These are the issues the build surfaced that the written spec did not anticipate.
Fold them into the spec (or just use the working repo, which already has them).

## 1. `lru_cache` on `Settings` is a runtime bug (important)

The v2 `api/deps.py` cached the factory with `@lru_cache` keyed on a `Settings`
argument. Pydantic models are **unhashable**, so the first real API request
raises `TypeError: unhashable type: 'Settings'`. This would not show up until
runtime.

**Fix:** cache a no-argument builder that resolves settings internally, and
expose a `reset_factory_cache()` for tests:

```python
@lru_cache(maxsize=1)
def _build_factory() -> ClientFactory:
    return ClientFactory(get_settings())

def reset_factory_cache() -> None:
    _build_factory.cache_clear()

def get_factory() -> ClientFactory:
    return _build_factory()
```

## 2. FastAPI `Depends()` in defaults trips ruff `B008`

Ruff's `B008` ("no function calls in argument defaults") fires on every
`Depends(...)` default — but that is the intended FastAPI pattern.

**Fix:** per-file ignore in `pyproject.toml`:

```toml
[tool.ruff.lint.per-file-ignores]
"src/cloud_relay/api/routers/*" = ["B008"]
"src/cloud_relay/api/deps.py" = ["B008"]
```

## 3. `SecretStr` is not a `str` under mypy strict

Passing a plain `str` to a model field typed `SecretStr | None` works at runtime
(Pydantic coerces) but fails `mypy --strict`. The CLI must wrap explicitly:

```python
from pydantic import SecretStr
CreateSecretRequest(name=name, secret_string=SecretStr(value), ...)
```

## 4. `list[BaseModel]` is invariant — use `Sequence`

`render(data: BaseModel | list[BaseModel])` rejects `list[SecretMetadata]` under
strict typing (list is invariant). Use the covariant `Sequence`, and discriminate
single-vs-many on `isinstance(data, BaseModel)` rather than `isinstance(data, list)`:

```python
from collections.abc import Sequence
def render(data: BaseModel | Sequence[BaseModel], fmt: str, *, show_secret=False) -> str: ...
# in each formatter:
payload = dump(data) if isinstance(data, BaseModel) else [dump(m) for m in data]
```

## 5. boto3-stubs typing on the client factory

`boto3-stubs` types `Session.client()` with per-service `Literal` overloads, so a
generic `service_name: str` plus a `**kwargs` dict matches no overload, and the
`retries` dict isn't a `_RetryDict`. Pass args explicitly and add two narrow
ignores; the public return stays `Any` by design:

```python
client = self._session.client(  # type: ignore[call-overload]
    service_name, config=self._boto_config(), endpoint_url=self._settings.endpoint_url,
)
# and on the retries dict: # type: ignore[arg-type]
```

Passing `endpoint_url=None` is equivalent to omitting it, so no conditional is
needed.

## 6. Test-environment notes (not code bugs)

- **moto S3 bucket names must be valid** (≥3 chars, dns-style). `"b"` fails; use
  `"test-bucket"`.
- **CLI/API build their own factory** from `get_settings()` (env-driven), so
  tests set `CLOUD_RELAY_REGION=us-east-1` via `monkeypatch.setenv` and call
  `reset_factory_cache()` inside the moto context so the factory is built mocked.

## Net

The architecture in the v2 spec held up exactly as designed — BaseService,
the factory, error translation, the formatter registry/protocol, thin adapters,
and the Option-A API shape all worked. Every fix above is a typing-strictness or
test-harness detail, except finding #1, which is a genuine latent runtime bug
worth carrying into any future spec.
