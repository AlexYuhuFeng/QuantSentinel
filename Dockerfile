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

# System deps (psycopg + build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
  && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python - \
  && ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Install dependencies first for better layer caching
COPY pyproject.toml poetry.lock* /app/
RUN poetry install --only main --no-root

# Copy source
COPY src/ /app/src/
COPY locales/ /app/locales/
COPY alembic.ini /app/alembic.ini
COPY src/quantsentinel/infra/db/migrations /app/src/quantsentinel/infra/db/migrations

# Install the project (editable not needed in container; regular install is fine)
RUN poetry install --only main

# Default command (compose will override per service)
CMD ["bash", "-lc", "streamlit run src/quantsentinel/app/main.py --server.port=8501 --server.address=0.0.0.0"]