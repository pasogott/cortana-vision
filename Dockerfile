# ---------- Base ----------
FROM python:3.11-slim

# ---------- Environment ----------
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PIP=1 \
    PATH="/root/.local/bin:$PATH"

WORKDIR /app

# ---------- System dependencies ----------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        tesseract-ocr \
        libglib2.0-0 \
        libsm6 \
        libxrender1 \
        libxext6 \
        build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ---------- Install uv ----------
RUN pip install --no-cache-dir uv

# ---------- Copy dependency files ----------
COPY pyproject.toml ./

# ---------- Install Python dependencies ----------
RUN uv pip compile pyproject.toml -o requirements.txt --generate-hashes --quiet && \
    uv pip install --system --no-cache -r requirements.txt

# ---------- Copy App Code ----------
COPY app ./app

# ---------- Create Directories ----------
RUN mkdir -p /app/uploads /app/tmp /app/data /app/keyframes && chmod -R 777 /app

# ---------- Expose Port ----------
EXPOSE 8000

# ---------- Default Entrypoint ----------
CMD ["python", "-m", "app.main"]
