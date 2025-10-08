# ---------- Base ----------
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PIP=1 \
    UV_LINK_MODE=copy \
    PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Install core OS dependencies including sqlite3
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    sqlite3 \
 && rm -rf /var/lib/apt/lists/*

# Install uv (fast dependency manager)
RUN pip install --no-cache-dir uv

# ---------- Dependency Layer ----------
# Copy only pyproject first (for build cache)
COPY pyproject.toml ./

# Compile deps into lockfile and install
RUN uv pip compile pyproject.toml -o requirements.txt --generate-hashes --quiet \
 && uv pip install --system --no-cache -r requirements.txt

# ---------- App Layer ----------
COPY app ./app
COPY .env .env

# Create tmp directory for processing frames
RUN mkdir -p /app/tmp

# ---------- Create Non-Root User and Set Permissions ----------
# Create a non-root user and group for the app
RUN useradd -m appuser

# Ensure the /app/data directory exists and change ownership to appuser
RUN mkdir -p /app/data && chown -R appuser:appuser /app /app/data

# ---------- Run ----------
# Switch to the non-root user to run the app
USER appuser

CMD ["python", "-m", "app.main"]
