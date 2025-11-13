# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install FFmpeg for video processing
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Install the project into `/workspace`
WORKDIR /workspace

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Ensure installed tools can be executed out of the box
ENV UV_TOOL_BIN_DIR=/usr/local/bin

# Copy workspace configuration files
COPY pyproject.toml uv.lock ./
COPY cortana_common ./cortana_common

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev

# Copy the service code
COPY services/sampler-worker ./services/sampler-worker

# Install the service
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/workspace/.venv/bin:$PATH"

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Run the sampler worker
CMD ["python", "-m", "services.sampler-worker.src"]
