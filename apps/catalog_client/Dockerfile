FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /srv

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-install-project --no-dev || uv sync --no-dev

COPY . .
RUN uv sync --no-dev

ENV PATH="/srv/.venv/bin:$PATH" \
    PYTHONPATH="/srv/src" \
    PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
