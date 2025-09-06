FROM python:3.13-slim AS base

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

# Install dependencies
COPY pyproject.toml README.md ./
RUN pip install --upgrade pip \
    && pip install .[dev] --no-cache-dir

# Copy source
COPY src ./src
COPY config.example.yaml ./

# Create non-root user
RUN useradd -m -u 10001 appuser \
    && mkdir -p /app/data /app/reports \
    && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "cleanmail.main", "serve"]
