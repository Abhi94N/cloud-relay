# cloud-relay documentation

Start with the top-level [README](../README.md) for the elevator pitch
and a quickstart. Use these docs when you need more depth.

## Documents

| Doc | Read this when… |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | …you need to understand how the code is shaped at runtime — layering rules, the diamond core/services/adapters model, request lifecycle, error model, where state lives, and where to look to extend something. |
| [USAGE.md](USAGE.md) | …you're *using* cloud-relay (library, CLI, or API) and want more than the README quickstart — the full CLI command tree, every config env var, AWS SSO setup, GovCloud, error handling patterns, and production operational notes. |
| [PACKAGING.md](PACKAGING.md) | …you need to ship a build — local install, wheel/sdist, a single-file CLI binary (PyInstaller / shiv), GitLab Package Registry, or PyPI. |
| [AWS_WRAPPER_SPEC_v2.md](AWS_WRAPPER_SPEC_v2.md) | …you want the **original build spec** (top-down "create these files in this order"). Useful as a rebuild reference; outdated in places where the implementation refined the design — see VALIDATION_FINDINGS for the diff. |
| [VALIDATION_FINDINGS.md](VALIDATION_FINDINGS.md) | …you're curious which issues the initial build surfaced that the spec didn't anticipate (`lru_cache` on Pydantic models, `Sequence[BaseModel]` invariance, etc.). All findings are already folded into the implementation. |

## How to read them

Most people only need **ARCHITECTURE** (mental model) + **USAGE** (how
to drive it). The spec and findings are historical artifacts kept for
reference; you don't need them to use or extend the project.

For *extending* the code with a new operation, new service, or new
cloud provider, see
[`src/cloud_relay/services/aws/s3/EXTENDING.md`](../src/cloud_relay/services/aws/s3/EXTENDING.md).
