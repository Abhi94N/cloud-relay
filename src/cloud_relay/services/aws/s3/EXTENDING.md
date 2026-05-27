# Adding an operation to a service

This four-step process applies to any service in any cloud package. S3 is a
scaffold: `head_object` is implemented as a worked example; the rest are stubs.

> **Adding a *new cloud* (GCP, Azure, …)?** Create
> `src/cloud_relay/services/<cloud>/_core/{config,auth,service,errors}.py`
> first — that gives the new package its own settings, client factory, base
> class, and SDK-to-domain error translator. Then follow the four steps below
> for each service.

## 1. Add the model(s) — `models.py`

Define a Pydantic request model and, if the call returns data, a response model.
Keep them pure data + validators. For list operations, model the page-flattened
result (a `list[...]`), not the raw SDK page shape.

## 2. Add the service method — `service.py`

On the `*Service` class, add a method that:

- takes the request model,
- builds the SDK kwargs,
- calls `self._client.<operation>(...)` inside `try/except <ProviderError>`,
- re-raises via `raise translate_error(e) from e`,
- returns the typed response model.

For anything that paginates, use `self._client.get_paginator(...)` and copy the
pattern in `SecretsManagerService.list_secrets`.

## 3. Add the API endpoint — `api/routers/aws/<service>.py`

Add a thin route that depends on the service via `Depends(get_<svc>_service)`
and wraps the sync call in `run_in_threadpool`. Use the service models directly
as request body and `response_model`. Do not translate errors here — the global
handler in `api/main.py` maps domain exceptions to HTTP status codes.

## 4. Add the CLI command — `cli/commands/aws/<service>.py`

Add a Typer command that pulls the `CliContext` off `ctx.obj`, constructs the
service, calls the method, and passes the result to `render(...)`. Never call
`print()` directly — all output goes through `cloud_relay.cli.output.render`.

## Checklist

- [ ] Request/response models added and validated
- [ ] Service method wraps the SDK error with `translate_error`
- [ ] Router endpoint added (thin, `run_in_threadpool`, `response_model` set)
- [ ] CLI command added (uses `render`, no direct printing)
- [ ] Tests: service (mocked), and a route/command smoke test
