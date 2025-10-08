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
    tesseract-ocr \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# -------------------------------------------------
# INSTALL UV (modern pip/poetry hybrid)
# -------------------------------------------------
RUN pip install --no-cache-dir uv

# -------------------------------------------------
# DEPENDENCY CACHE LAYER
# -------------------------------------------------
COPY pyproject.toml ./

RUN uv pip compile pyproject.toml -o requirements.txt --generate-hashes --quiet \
 && uv pip install --system --no-cache -r requirements.txt

# -------------------------------------------------
# APPLICATION LAYER
# -------------------------------------------------
COPY app ./app
COPY .env .env

RUN mkdir -p /app/tmp /app/data /app/uploads && chmod -R 777 /app

# -------------------------------------------------
# SECURITY: NON-ROOT USER
# -------------------------------------------------
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# -------------------------------------------------
# CMD (Entrypoint)
# -------------------------------------------------
CMD ["python", "-m", "app.main"]
