# Use NVIDIA CUDA runtime as base image for GPU support
FROM nvidia/cuda:12.9.1-runtime-ubuntu22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV OLLAMA_HOST=0.0.0.0
ENV OLLAMA_PORT=11434

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Create app directory
WORKDIR /app

# Copy Python requirements and install dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY api_server.py .
COPY startup.sh .
RUN chmod +x startup.sh

# Create directory for model storage
RUN mkdir -p /root/.ollama

# Expose ports
EXPOSE 11434 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start script that launches both Ollama and the API server
CMD ["./startup.sh"] 