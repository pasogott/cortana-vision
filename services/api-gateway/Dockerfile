# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

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
COPY services/api-gateway ./services/api-gateway

# Install the service
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/workspace/.venv/bin:$PATH"

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Run the FastAPI application by default
# Uses `fastapi run` for production-optimized server with uvicorn
# Uses `--host 0.0.0.0` to allow access from outside the container
CMD ["fastapi", "run", "--host", "0.0.0.0", "--port", "8000", "services/api-gateway/src"]
