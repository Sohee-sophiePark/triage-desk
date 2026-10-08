# ── Stage 1: Install production dependencies ──────────────────────────────────
FROM python:3.10-slim AS deps

# Install uv (pinned version for reproducibility)
COPY --from=ghcr.io/astral-sh/uv:0.8.11 /uv /usr/local/bin/uv

WORKDIR /app

# Copy lockfile and project metadata — nothing else yet
# uv resolves from uv.lock exactly (--frozen) and skips the project itself (package=false)
COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev


# ── Stage 2: Production image ─────────────────────────────────────────────────
FROM python:3.10-slim AS production

WORKDIR /app

# Security: non-root user
RUN groupadd -r triagedesk && useradd -r -g triagedesk -d /app -s /sbin/nologin triagedesk

# Copy the resolved virtualenv from the deps stage
COPY --from=deps /app/.venv /app/.venv

# Make .venv binaries the default
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

RUN chown -R triagedesk:triagedesk /app
USER triagedesk

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

EXPOSE 8000

# Production: Gunicorn with Uvicorn workers (4 workers for 2-core hosts)
CMD ["gunicorn", "app.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]
