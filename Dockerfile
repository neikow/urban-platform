FROM node:20-bookworm-slim AS assets
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run styles:build

FROM python:3.13-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_NO_DEV=1

RUN apt-get update && apt-get install -y \
    libpq5 \
    gettext \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m appuser && chown appuser /app -R
USER appuser

ENV PATH="/app/.venv/bin:$PATH"

COPY --chown=appuser:appuser . .

COPY --from=assets --chown=appuser:appuser /app/urban_platform/static/css/styles.css /app/urban_platform/static/css/styles.css

RUN uv sync --locked

ENV DJANGO_SETTINGS_MODULE="urban_platform.settings.production"

RUN SECRET_KEY=dummy \
    DB_NAME=dummy \
    DB_USER=dummy \
    DB_PASSWORD=dummy \
    DB_HOST=dummy \
    DB_PORT=5432 \
    uv run manage.py collectstatic --noinput

RUN SECRET_KEY=dummy \
    DB_NAME=dummy \
    DB_USER=dummy \
    DB_PASSWORD=dummy \
    DB_HOST=dummy \
    DB_PORT=5432 \
    uv run manage.py compilemessages

# Run application
CMD ["/app/.venv/bin/gunicorn", "urban_platform.wsgi:application", "--bind", "0.0.0.0:8000"]
