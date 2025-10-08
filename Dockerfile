# ---------- Base ----------
FROM python:3.11-slim

# ---------- Env ----------
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# ---------- System dependencies ----------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        tesseract-ocr \
        tesseract-ocr-deu \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ---------- Install uv ----------
RUN pip install --no-cache-dir uv

# ---------- Copy dependency files ----------
COPY pyproject.toml requirements.txt ./

# ---------- Install Python dependencies ----------
RUN uv pip install --system --no-cache --upgrade pip setuptools wheel && \
    uv pip install --system -r requirements.txt

# ---------- Copy App ----------
COPY . .

# ---------- Create necessary directories ----------
RUN mkdir -p /app/uploads /app/keyframes /app/data && chmod -R 777 /app

# ---------- Expose & Run ----------
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
