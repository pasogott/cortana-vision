FROM nvidia/cuda:11.8.0-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Africa/Lagos
ENV PATH="/root/.local/bin:/root/.cargo/bin:${PATH}"

WORKDIR /app

RUN apt update && apt install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt update && \
    apt install -y \
        build-essential \
        python3.12 \
        python3.12-venv \
        python3.12-dev \
        git \
        git-lfs \
        cmake \
        curl && \
    git lfs install && \
    rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

COPY . /app

RUN /root/.local/bin/uv venv && \
    /root/.local/bin/uv pip install -U vllm --pre --extra-index-url https://wheels.vllm.ai/nightly && \
    /root/.local/bin/uv pip install -e .

ENV PYTHONPATH="/app"

EXPOSE 8050

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8050", "--access-log"]