# -------------------------------------------------
# BASE IMAGE
# -------------------------------------------------
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PIP=1 \
    UV_LINK_MODE=copy \
    PATH="/root/.local/bin:$PATH" \
    # 🔥 IMPORTANT: Set prefix ABOVE tessdata folder
    TESSDATA_PREFIX="/usr/share/tesseract-ocr/5/tessdata"

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
    ca-certificates \
    wget \
    tesseract-ocr && \
    rm -rf /var/lib/apt/lists/*

# -------------------------------------------------
# LANGUAGE DATA (ONLY German + English)
# -------------------------------------------------
RUN mkdir -p ${TESSDATA_PREFIX}/tessdata && \
    cd ${TESSDATA_PREFIX}/tessdata && \
    wget -q https://github.com/tesseract-ocr/tessdata_best/raw/main/deu.traineddata && \
    wget -q https://github.com/tesseract-ocr/tessdata_best/raw/main/eng.traineddata && \
    wget -q https://github.com/tesseract-ocr/tessdata_best/raw/main/osd.traineddata

# ✅ Verify presence and print paths
RUN echo "[VERIFY] Listing tessdata:" && ls -lh ${TESSDATA_PREFIX}/tessdata && \
    echo "[VERIFY] Tesseract languages:" && tesseract --list-langs

# -------------------------------------------------
# INSTALL UV (modern pip)
# -------------------------------------------------
RUN pip install --no-cache-dir uv

# -------------------------------------------------
# DEPENDENCIES
# -------------------------------------------------
COPY pyproject.toml ./ 
RUN uv pip compile pyproject.toml -o requirements.txt --generate-hashes --quiet && \
    uv pip install --system --no-cache -r requirements.txt



# -------------------------------------------------
# APPLICATION
# -------------------------------------------------
COPY app ./app
COPY .env .env
RUN mkdir -p /app/tmp /app/data /app/uploads && chmod -R 777 /app

# -------------------------------------------------
# SECURITY
# -------------------------------------------------
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# -------------------------------------------------
# CMD
# -------------------------------------------------
CMD ["python", "-m", "app.main"]
