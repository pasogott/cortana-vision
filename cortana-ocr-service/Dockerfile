FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PIP=1 \
    UV_LINK_MODE=copy \
    PATH="/root/.local/bin:$PATH" \
    HF_HOME=/app/hf-cache

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    wget \
    git \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6 \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
RUN uv pip compile pyproject.toml -o requirements.txt --generate-hashes --quiet && \
    uv pip install --system --no-cache -r requirements.txt

COPY app ./app
COPY .env .env

RUN mkdir -p /app/tmp /app/data /app/uploads /app/hf-cache && \
    chmod -R 777 /app

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "app.main"]
