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

ARG SENTRY_RELEASE
ENV SENTRY_RELEASE=${SENTRY_RELEASE}

RUN apt-get update && apt-get install -y \
    libpq5 \
    gettext \
    git \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/app/.venv/bin:$PATH"

COPY . .

COPY --from=assets /app/urban_platform/static/css/styles.css /app/urban_platform/static/css/styles.css

RUN uv sync --locked

ENV DJANGO_SETTINGS_MODULE="urban_platform.settings.production"

ARG SECRET_KEY=build-only-secret-key
ARG DB_NAME=build
ARG DB_USER=build
ARG DB_PASSWORD=build
ARG DB_HOST=localhost
ARG DB_PORT=5432

RUN python manage.py collectstatic --noinput
RUN python manage.py compilemessages

CMD ["gunicorn", "urban_platform.wsgi:application", "--bind", "0.0.0.0:8000"]
