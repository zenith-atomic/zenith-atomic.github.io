FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for native Python wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source directories
COPY data_pipeline/ ./data_pipeline/
COPY execution/ ./execution/
COPY strategies/ ./strategies/
COPY risk/ ./risk/
COPY knowledge/ ./knowledge/
COPY dashboard/ ./dashboard/
COPY configs/ ./configs/

# Copy main entry point
COPY main.py .

# Create data directories
RUN mkdir -p /app/logs

# Health check
# HEALTHCHECK disabled - bot runs to completion in paper mode

# Expose port for bot API (if any)
EXPOSE 8000

# Run main orchestrator
CMD ["python", "main.py"]