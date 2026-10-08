FROM python:3.13-slim-bookworm AS docs
RUN pip install --no-cache-dir mkdocs-material
WORKDIR /app
COPY docs/ docs/
RUN cd docs && mkdocs build

FROM node:24-bookworm-slim AS assets
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run typecheck && npm run build

FROM python:3.13-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_NO_DEV=1

ARG SENTRY_RELEASE
ENV SENTRY_RELEASE=${SENTRY_RELEASE}
# Reported by /healthz/, for the deployment agent (defaults to SENTRY_RELEASE).
ARG APP_VERSION
ENV APP_VERSION=${APP_VERSION}

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    gettext \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/app/.venv/bin:$PATH"

COPY . .

COPY --from=assets /app/urban_platform/static/dist /app/urban_platform/static/dist
COPY --from=docs /app/docs/site /app/docs/site

RUN uv sync --locked

# Self-hosted basemap: the worker extracts the territory's tiles (publications.map_tiles).
COPY --from=protomaps/go-pmtiles:v1.31.2 /go-pmtiles /usr/local/bin/pmtiles

ENV DJANGO_SETTINGS_MODULE="urban_platform.settings.production"

ARG SECRET_KEY=build-only-secret-key
ARG DB_NAME=build
ARG DB_USER=build
ARG DB_PASSWORD=build
ARG DB_HOST=localhost
ARG DB_PORT=5432

RUN python manage.py compilemessages

# Drop root: run as an unprivileged user. Done last so the build steps above
# (uv sync, compilemessages) still run as root, then ownership is handed over.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/staticfiles /app/mediafiles \
    && chown -R appuser:appuser /app
USER appuser

CMD ["gunicorn", "urban_platform.wsgi:application", "-c", "gunicorn.conf.py"]
