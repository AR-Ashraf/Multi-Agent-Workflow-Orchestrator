# Cadenza FastAPI gateway. Build context is the REPO ROOT (it needs the
# orchestrator path-dependency at packages/orchestrator).
#   docker build -f apps/api/Dockerfile -t cadenza-api .
# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1
WORKDIR /app/apps/api

# The path-dep (pure-Python orchestrator) must be present for `uv sync`.
COPY packages/orchestrator /app/packages/orchestrator

# Dependency layer — cached unless the lock or project metadata changes.
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# App source + install the project itself.
COPY apps/api/src ./src
RUN uv sync --frozen --no-dev

# Use the synced virtualenv directly at runtime — no `uv` (and no writable uv
# cache) needed for an unprivileged user.
ENV PATH="/app/apps/api/.venv/bin:$PATH"

# Run unprivileged.
RUN useradd -r -u 10001 cadenza && chown -R cadenza /app
USER cadenza

EXPOSE 8000
CMD ["uvicorn", "cadenza_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
