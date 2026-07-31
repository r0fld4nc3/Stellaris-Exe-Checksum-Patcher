# Install uv
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV NUITKA_CACHE_DIR=/app/.ccache

# Install our platform dependencies
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    build-essential \
    ccache \
    libbrotli-dev \
    libglib2.0-dev \
    libkrb5-dev \
    patchelf

# Change the working directory to the `app` directory
WORKDIR /app

# Install project dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Copy the project into the image
COPY . /app

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked