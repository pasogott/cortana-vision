# -------------------------------------------------
# BASE IMAGE
# -------------------------------------------------
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PIP=1 \
    UV_LINK_MODE=copy \
    PATH="/root/.local/bin:$PATH"

WORKDIR /app

# -------------------------------------------------
# SYSTEM DEPENDENCIES
# -------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    sqlite3 \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# -------------------------------------------------
# INSTALL UV (modern pip/poetry hybrid)
# -------------------------------------------------
RUN pip install --no-cache-dir uv

# -------------------------------------------------
# DEPENDENCY CACHE LAYER
# -------------------------------------------------
# Copy dependency manifest first to leverage Docker cache
COPY pyproject.toml ./

# Pre-compile & install dependencies
RUN uv pip compile pyproject.toml -o requirements.txt --generate-hashes --quiet \
 && uv pip install --system --no-cache -r requirements.txt

# -------------------------------------------------
# APPLICATION LAYER
# -------------------------------------------------
# Copy application source
COPY app ./app
COPY .env .env

# Create writable directories
RUN mkdir -p /app/tmp /app/data /app/uploads && chmod -R 777 /app

# -------------------------------------------------
# SECURITY: NON-ROOT USER
# -------------------------------------------------
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# -------------------------------------------------
# ARG / ENV FOR MODE (dev or prod)
# -------------------------------------------------
ARG MODE=prod
ENV MODE=${MODE}

# -------------------------------------------------
# ENTRYPOINT LOGIC
# -------------------------------------------------
# The actual command is injected via docker-compose.
# Default (safe) fallback if not overridden:
CMD ["python", "-m", "app.main"]
