# syntax=docker/dockerfile:1.7
FROM python:3.13-slim

# System dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=America/New_York

WORKDIR /app

# Upgrade pip
RUN python -m pip install --upgrade pip

# Optionally install extras (e.g., dev) in the image
ARG INSTALL_EXTRAS=""

# Install app and its dependencies from pyproject.toml
COPY pyproject.toml README.md ./
COPY src ./src
RUN if [ -n "$INSTALL_EXTRAS" ]; then \
      pip install --no-cache-dir ".[${INSTALL_EXTRAS}]" ; \
    else \
      pip install --no-cache-dir . ; \
    fi

# Copy example config
COPY config.example.yaml ./

# Create non-root user
RUN useradd -m -u 10001 appuser \
    && mkdir -p /app/data /app/reports \
    && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "cleanmail.main", "serve"]
