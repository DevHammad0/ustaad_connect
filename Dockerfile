# Stage 1: Builder
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app

# Install dependencies using uv
# We copy pyproject.toml and uv.lock first to leverage Docker layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy the rest of the application code
COPY . .
RUN uv sync --frozen --no-dev

# Stage 2: Runtime
FROM python:3.13-slim-bookworm AS runtime

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/pyproject.toml /app/pyproject.toml

# Expose port (Cloud Run defaults to 8080, standard FastAPI defaults to 8000)
# We will read the PORT environment variable if provided, otherwise default to 8000
EXPOSE 8080

# Start the FastAPI server using the uv virtual environment and uvicorn
CMD ["/app/.venv/bin/uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
