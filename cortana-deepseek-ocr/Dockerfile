FROM nvidia/cuda:11.8.0-devel-ubuntu22.04

WORKDIR /app

# Install Python and system dependencies
RUN apt update && apt install -y \
    python3.12 python3.12-venv git git-lfs curl && \
    git lfs install && \
    rm -rf /var/lib/apt/lists/*

# Install uv globally
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy project files
COPY . /app

# Create virtual environment and install dependencies using uv
RUN uv venv && uv pip install -r requirements.txt

# Expose service port
EXPOSE 8050

# Run the OCR FastAPI service using uv
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8050", "--access-log"]
