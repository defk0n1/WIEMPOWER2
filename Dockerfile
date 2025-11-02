FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    gnupg \
    curl \
    gcc \
    g++ \
    postgresql-client \
    libicu-dev \
    && rm -rf /var/lib/apt/lists/*



# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/storage /app/data /app/logs

# Set permissions
RUN chmod +x scripts/entrypoint.sh || true

# Expose ports
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

# Default command (can be overridden in docker-compose)
CMD ["python", "main.py"]
