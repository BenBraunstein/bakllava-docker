#!/bin/bash

# Enable strict error handling
set -e

echo "Starting Bakllava Docker Container..."

# Check Ollama installation
OLLAMA_BINARY="/usr/local/bin/ollama"
echo "Checking Ollama at: $OLLAMA_BINARY"

if [ ! -f "$OLLAMA_BINARY" ]; then
    echo "FATAL: Ollama binary not found at $OLLAMA_BINARY"
    exit 1
fi

if [ ! -x "$OLLAMA_BINARY" ]; then
    echo "FATAL: Ollama binary not executable at $OLLAMA_BINARY"
    exit 1
fi

echo "Ollama version:"
$OLLAMA_BINARY --version

# Function to handle shutdown
cleanup() {
    echo "Shutting down services..."
    if [ ! -z "$OLLAMA_PID" ]; then
        kill $OLLAMA_PID 2>/dev/null || true
    fi
    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null || true
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Start Ollama service in the background
echo "Starting Ollama service..."
$OLLAMA_BINARY serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "Waiting for Ollama to be ready..."
timeout=180
counter=0
while ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
    if [ $counter -ge $timeout ]; then
        echo "ERROR: Ollama failed to start within $timeout seconds"
        echo "Checking if Ollama process is running..."
        ps aux | grep ollama || echo "No Ollama process found"
        echo "Checking Ollama logs..."
        tail -20 /root/.ollama/logs/server.log 2>/dev/null || echo "No Ollama logs found"
        echo "Checking port 11434..."
        netstat -tlnp | grep 11434 || echo "Port 11434 not listening"
        exit 1
    fi
    sleep 1
    counter=$((counter + 1))
    if [ $((counter % 15)) -eq 0 ]; then
        echo "Still waiting for Ollama... ($counter/$timeout seconds)"
    fi
done

echo "Ollama is ready!"

# Pull the Bakllava model if not already present
echo "Checking for Bakllava model..."
if ! curl -s http://localhost:11434/api/tags | grep -q "bakllava"; then
    echo "Pulling Bakllava model (this may take a while)..."
    $OLLAMA_BINARY pull bakllava
    echo "Bakllava model pulled successfully!"
else
    echo "Bakllava model already available"
fi

# Start the FastAPI server
echo "Starting FastAPI server..."
cd /app
python3 api_server.py &
API_PID=$!

echo "Services started successfully!"
echo "- Ollama API: http://localhost:11434"
echo "- FastAPI server: http://localhost:8000"
echo "- API documentation: http://localhost:8000/docs"

# Wait for either process to exit
wait 