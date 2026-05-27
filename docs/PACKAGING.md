# Packaging

How to build cloud-relay locally, install it from a local artifact, ship
a single-file CLI binary, and publish to the GitLab Package Registry (or
PyPI later).

## 1. Local development install (the common case)

You don't need to "build" anything to work on the repo. `uv sync` creates
an editable install:

```bash
uv sync --all-extras      # everything (lib + cli + api + dev tools)
uv sync --extra cli       # lib + cli only
uv sync --extra api       # lib + api only
uv sync                   # lib only
```

`uv run cloud-relay --help`, `uv run pytest`, etc. all work against the
editable copy. Any code change is picked up on the next invocation
without rebuilding.

## 2. Build a local wheel + sdist

When you want a distributable artifact (to install elsewhere, hand to a
colleague, or upload to a registry):

```bash
uv build
ls dist/
# cloud_relay-0.1.0-py3-none-any.whl
# cloud_relay-0.1.0.tar.gz
```

`uv build` runs PEP 517 with the **hatchling** backend configured in
[`pyproject.toml`](../pyproject.toml). It produces two artifacts:

- **Wheel** (`.whl`) — what `pip install` consumes for fast installs.
  Contains only `src/cloud_relay/` (the import target).
- **Sdist** (`.tar.gz`) — the full source tree including tests, docs,
  and `pyproject.toml`. Use this for archival, reproducibility, or when
  someone needs to build the wheel on an unusual platform.

`docs/` ships in the sdist (it's not excluded by hatchling's defaults)
but not in the wheel — wheels are for runtime, not documentation.

## 3. Install the local build elsewhere

### 3.1 Into another uv project

```bash
uv add /path/to/cloud-relay/dist/cloud_relay-0.1.0-py3-none-any.whl
# or, for the extras:
uv add "cloud-relay[api] @ file:///path/to/cloud-relay/dist/cloud_relay-0.1.0-py3-none-any.whl"
```

### 3.2 Into any venv with `pip`

```bash
pip install /path/to/cloud-relay/dist/cloud_relay-0.1.0-py3-none-any.whl
pip install '/path/to/cloud-relay/dist/cloud_relay-0.1.0-py3-none-any.whl[cli,api]'
```

### 3.3 As a global user tool (CLI only, isolated venv)

```bash
uv tool install --from /path/to/cloud-relay/dist/cloud_relay-0.1.0-py3-none-any.whl \
    "cloud-relay[cli]"
cloud-relay --help     # available on $PATH
```

`pipx install` does the same thing.

## 4. Ship the CLI as a single-file binary

For users who don't have Python (or shouldn't need to know they do), the
standard answer is **PyInstaller**. It bundles the Python interpreter
and all dependencies into one executable per OS.

> Tradeoffs to know up front:
> - **One build per OS / arch.** A Linux binary will not run on macOS or
>   Windows. Build on the target platform (or in a matching container /
>   CI runner).
> - **Size.** boto3 + botocore + pydantic + typer + rich is ~30–60 MB
>   bundled. boto3's per-service data files dominate.
> - **Cold start.** Single-file binaries unpack to a temp dir on first
>   run, adding ~300–800 ms vs a normal Python invocation. Use
>   `--onedir` instead of `--onefile` if startup matters more than
>   distribution simplicity.
> - **Antivirus false positives.** PyInstaller binaries sometimes trip
>   Windows Defender heuristics; signing the binary on Windows is the
>   long-term fix.

### 4.1 Build it

```bash
# Run PyInstaller without polluting the project deps:
uvx --from "pyinstaller>=6" pyinstaller \
    --onefile \
    --name cloud-relay \
    --collect-all cloud_relay \
    --collect-all botocore \
    --collect-all boto3 \
    src/cloud_relay/cli/main.py

ls dist/
# cloud-relay   (the executable)
./dist/cloud-relay --help
./dist/cloud-relay aws secrets-manager list
```

Notes on the flags:

- `--onefile` — single executable. Use `--onedir` for a folder with the
  binary + deps if cold-start latency matters.
- `--name cloud-relay` — what the output binary is called.
- `--collect-all cloud_relay` — pull in all submodules of our package.
  PyInstaller's static analyzer sometimes misses dynamically-imported
  submodules; this is the safe answer.
- `--collect-all botocore --collect-all boto3` — boto3 dynamically loads
  service data files; PyInstaller cannot see those imports. Without
  these you'll get `DataNotFoundError` at runtime.
- The entry point is [src/cloud_relay/cli/main.py](../src/cloud_relay/cli/main.py),
  which already has an `if __name__ == "__main__": run()` block.

If you hit a missing-import error at runtime, add it with
`--hidden-import <module>`. For repeat builds, generate a `.spec` file
(`pyi-makespec ...`) and check it in.

### 4.2 Lighter-weight alternative: `shiv`

If your users have Python already, `shiv` builds a single `.pyz` zipapp
that's ~10 MB instead of ~50 MB, and starts faster than PyInstaller:

```bash
uvx --from shiv shiv \
    --console-script cloud-relay \
    --output-file dist/cloud-relay.pyz \
    --compressed \
    .[cli]
./dist/cloud-relay.pyz aws secrets-manager list
```

`.pyz` requires Python `>=3.11` on the target. PyInstaller does not.

### 4.3 When to use which

| Scenario | Use |
|---|---|
| User has Python | `uv tool install` / `pipx install` / `shiv` |
| User does NOT have Python | PyInstaller |
| Sub-second cold start required | PyInstaller `--onedir` (not `--onefile`) |
| Multiple OSes from one CI | PyInstaller, one build per target runner |

## 5. Publishing to GitLab Package Registry

GitLab provides a PyPI-style index per project. The pipeline to publish
is included as **[`.gitlab-ci.yml`](../.gitlab-ci.yml) but commented out
by default** — uncomment when you're ready.

### 5.1 Manual publish (one-off)

```bash
uv build
twine upload \
    --repository-url https://gitlab.com/api/v4/projects/<PROJECT_ID>/packages/pypi \
    --username gitlab-ci-token \
    --password "<your-deploy-token>" \
    dist/*
```

Generate a deploy token at *Settings → Repository → Deploy tokens* with
the `write_package_registry` scope.

### 5.2 Via CI on tag

Uncomment `.gitlab-ci.yml`, push a tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The `publish` job runs only when `$CI_COMMIT_TAG` is set. It uses
`$CI_JOB_TOKEN` (auto-injected) which has scope to publish to the
project's own registry — no manual token needed.

### 5.3 Consumers install with

```bash
pip install \
    --extra-index-url "https://__token__:<deploy-token>@gitlab.com/api/v4/projects/<PROJECT_ID>/packages/pypi/simple" \
    "cloud-relay[api]"
```

Or, more durably, configure it in the consumer's `pyproject.toml` /
`pip.conf` / `uv.toml` so the token lives in one place.

## 6. Publishing to PyPI (when / if it goes public)

The same `uv build` artifacts upload to PyPI:

```bash
uv build
twine upload dist/*       # uses $TWINE_USERNAME=__token__, $TWINE_PASSWORD=<pypi-token>
```

Recommended: set up **PyPI Trusted Publishing** from GitLab so no token
ever lives in CI. See <https://docs.pypi.org/trusted-publishers/>.

Before you publish publicly, do the basics:

- [ ] Add a `LICENSE` file at the repo root.
- [ ] Fill in `authors`, `license`, `urls`, and `classifiers` in
      `[project]` of `pyproject.toml`.
- [ ] Confirm the project name is available on PyPI:
      `pip index versions cloud-relay`. If taken, rename in
      `pyproject.toml`'s `name` field (the import path stays
      `cloud_relay`).
- [ ] Decide a versioning policy. Hand-bumping `version = "0.1.0"` works
      until it doesn't; switching to `hatch-vcs` (reads from git tags)
      removes that toil.

## 7. Reproducibility

cloud-relay pins runtime + dev deps in `uv.lock`. To install exactly
what CI installed:

```bash
uv sync --frozen --all-extras
```

`--frozen` refuses to update the lockfile, so any drift between your
machine and CI shows up as a failure rather than a silent re-resolve.
