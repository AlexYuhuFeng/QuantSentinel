# QuantSentinel - single image used by: web / worker / beat
# Python version MUST match pyproject + CI (3.12)

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

# System deps (psycopg + TLS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    build-essential \
    libpq-dev \
  && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python - \
  && ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Create non-root user (production best practice)
RUN useradd -m -u 10001 appuser \
  && chown -R appuser:appuser /app

# -----------------------------
# Dependency layer
# -----------------------------
FROM base AS deps

COPY pyproject.toml poetry.lock* /app/
RUN poetry install --only main --no-ansi

# -----------------------------
# Runtime image
# -----------------------------
FROM base AS runtime

# Copy installed site-packages from deps
COPY --from=deps /usr/local /usr/local

# Copy app code
COPY src/ /app/src/
COPY locales/ /app/locales/
COPY alembic.ini /app/alembic.ini

# Ensure ownership
RUN chown -R appuser:appuser /app
USER appuser

# Default command (docker-compose overrides per service)
CMD ["bash", "-lc", "streamlit run src/quantsentinel/app/main.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false"]

# -----------------------------
# Dev image (optional target)
# -----------------------------
FROM runtime AS dev

USER root
COPY pyproject.toml poetry.lock* /app/
# Install dev deps for lint/test in container
RUN poetry install --with dev --no-ansi
RUN chown -R appuser:appuser /app
USER appuser