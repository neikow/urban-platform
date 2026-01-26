# Use an official Python runtime based on Debian 12 "bookworm" as a parent image.
FROM python:3.13-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install system packages
RUN apt-get update && apt-get install -y \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for Tailwind
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Install Node dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy the rest of the application
COPY . .

# Build styles
RUN npm run styles:build

# Install the project itself
RUN uv sync --frozen --no-dev

# Collect static files
# We need to set dummy env vars for collectstatic to work without a real DB or secrets
RUN SECRET_KEY=dummy \
    DB_NAME=dummy \
    DB_USER=dummy \
    DB_PASSWORD=dummy \
    DB_HOST=dummy \
    DB_PORT=5432 \
    uv run python manage.py collectstatic --noinput

# Run with gunicorn
CMD ["uv", "run", "gunicorn", "urban_platform.wsgi:application", "--bind", "0.0.0.0:8000"]
