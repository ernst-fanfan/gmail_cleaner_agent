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

# Install Python dependencies from requirements first (better layer caching)
COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy project files and install the local package
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# Copy config/example config
COPY config.example.yaml ./

# Create non-root user
RUN useradd -m -u 10001 appuser \
    && mkdir -p /app/data /app/reports \
    && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "cleanmail.main", "serve"]
