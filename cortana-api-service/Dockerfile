# Use a Python base image (choose the version you want)
FROM python:3.11-slim

# Install bash, curl, build-essential, and SQLite for the project
RUN apt-get update && apt-get install -y curl build-essential bash sqlite3

# Install 'uv' - uv is a tool for managing Python dependencies (like Poetry)
RUN pip install uv

# Set the working directory inside the container
WORKDIR /app

# Create a user (non-root) to run the application
RUN useradd -m appuser

# Change ownership of the application directory to the new user (appuser)
RUN chown -R appuser:appuser /app

# Copy pyproject.toml and other necessary files for uv to install dependencies
COPY pyproject.toml /app/

# Install dependencies via uv
RUN bash -c "uv pip install --system --no-cache -r <(uv pip compile --generate-hashes --quiet pyproject.toml)"

# Copy the rest of the application code
COPY ./app /app/

# Change ownership of the application code (including database) to the new user
RUN chown -R appuser:appuser /app

# Expose the necessary port for FastAPI
EXPOSE 8000

# Switch to the non-root user (appuser) for running the application
USER appuser

# Start the FastAPI app with Uvicorn (using uvicorn to serve FastAPI)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
