# Use Python 3.10 slim image as base
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV HF_HOME=/home/appuser/.cache/huggingface
ENV TRANSFORMERS_CACHE=/home/appuser/.cache/huggingface
ENV HF_HUB_OFFLINE=0
ENV HF_HUB_DISABLE_TELEMETRY=1
ENV HF_HUB_CACHE=/home/appuser/.cache/huggingface

# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create SSH directory and set permissions
RUN mkdir -p /home/appuser/.ssh && \
    chmod 700 /home/appuser/.ssh

# Create cache directory for Hugging Face and set permissions
RUN mkdir -p /home/appuser/.cache/huggingface/hub && \
    mkdir -p /home/appuser/.cache/huggingface/transformers && \
    chown -R appuser:appuser /home/appuser/.cache && \
    chmod -R 755 /home/appuser/.cache

# Switch to appuser to create additional directories
USER appuser
# Create a temporary file to ensure the user can write to the cache directory
RUN touch /home/appuser/.cache/huggingface/.test_write && rm /home/appuser/.cache/huggingface/.test_write
USER root

# Copy and run cache cleanup script
COPY clean_cache.py .
RUN python clean_cache.py

# Copy initialization script
COPY init_cache.sh .
RUN chmod +x init_cache.sh

# Copy entrypoint script
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Create necessary directories for logs
RUN mkdir -p /var/ossec/logs/archives && \
    chown -R appuser:appuser /app /var/ossec/logs /home/appuser/.ssh

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["./entrypoint.sh"]