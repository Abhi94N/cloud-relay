# syntax=docker/dockerfile:1.7
#
# cloud-relay API image.
#
# Base images are pulled from AWS Public ECR (public.ecr.aws) rather than
# Docker Hub to avoid Docker Hub's anonymous-pull rate limits in CI.
# AWS Public ECR mirrors the official Python images.
#
# Build:
#   docker build -t cloud-relay-api .
# Run:
#   docker run --rm -p 8000:8000 \
#     -e AWS_REGION=us-east-1 \
#     -e AWS_ACCESS_KEY_ID=... -e AWS_SECRET_ACCESS_KEY=... \
#     cloud-relay-api
#
# In production prefer an IAM role (instance profile / ECS task role / IRSA)
# over static keys -- boto3 picks those up automatically.

ARG PYTHON_VERSION=3.12
ARG BASE=public.ecr.aws/docker/library/python:${PYTHON_VERSION}-slim

# ---------- builder ----------
FROM ${BASE} AS builder

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_NO_PROGRESS=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN pip install --no-cache-dir uv

# Copy only what's needed to resolve and install deps. README.md is required
# because pyproject.toml references it as the project readme.
COPY pyproject.toml uv.lock README.md ./
COPY src ./src

# --no-editable installs the project as a regular wheel so the runtime
# stage doesn't need src/ on disk -- everything lives in .venv.
# --no-dev skips dev tooling (pytest, ruff, mypy, moto).
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --extra api --no-dev --no-editable

# ---------- runtime ----------
FROM ${BASE} AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

# Non-root user. UID 1000 matches the default in most base images and is
# friendly to bind-mounted volumes during local development.
RUN useradd --create-home --uid 1000 app && chown -R app /app
USER app

EXPOSE 8000

# Hit /healthz via stdlib urllib so we don't have to install curl/wget.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import sys, urllib.request; \
sys.exit(0 if urllib.request.urlopen('http://localhost:8000/healthz', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "cloud_relay.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
