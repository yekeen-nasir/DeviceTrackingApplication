# Use official Python slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy pyproject.toml and README first (for dependency install)
COPY pyproject.toml README.md ./

# Install Python dependencies
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -e .

# Copy the rest of the application code
COPY apps/ ./apps/
COPY libs/ ./libs/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Create a non-root user for running the app
RUN useradd -m -u 1000 tracker && chown -R tracker:tracker /app
USER tracker

# Expose the server port from .env (default 8000 if not set)
ARG SERVER_PORT=8000
EXPOSE ${SERVER_PORT}

# Health check using server port from .env
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${SERVER_PORT}/healthz || exit 1

# Default command to run your server
CMD ["python", "-m", "apps.tracker_server.main"]
