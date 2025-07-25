.PHONY: help build build-cpu up down logs test clean gpu-test install-test-deps cpu-test up-cpu

# Default target
help:
	@echo "Available commands:"
	@echo "  build            - Build the Docker image (GPU version)"
	@echo "  build-cpu        - Build the Docker image (CPU version)"
	@echo "  up               - Start the services (with GPU)"
	@echo "  up-cpu           - Start the services (CPU only)"
	@echo "  down             - Stop the services"
	@echo "  logs             - Show container logs"
	@echo "  test             - Run API tests (with GPU)"
	@echo "  cpu-test         - Run API tests (CPU only, slower but no GPU needed)"
	@echo "  install-test-deps - Install test dependencies"
	@echo "  clean            - Clean up containers and volumes"
	@echo "  gpu-test         - Test GPU availability"
	@echo "  dev              - Run in development mode"

# Install test dependencies
install-test-deps:
	@echo "Installing test dependencies..."
	pip3 install -r requirements-test.txt

# Build the Docker image (GPU version)
build:
	docker-compose build

# Build the Docker image (CPU version)
build-cpu:
	@echo "Building CPU-only Docker image..."
	docker-compose -f docker-compose.cpu.yml build

# Start services with GPU
up:
	docker-compose up -d

# Start services CPU-only (no GPU required)
up-cpu:
	@echo "Starting CPU-only mode (no GPU required)..."
	docker-compose -f docker-compose.cpu.yml up -d

# Start services with logs
up-logs:
	docker-compose up

# Start services CPU-only with logs
up-cpu-logs:
	docker-compose -f docker-compose.cpu.yml up

# Stop services
down:
	docker-compose down
	docker-compose -f docker-compose.cpu.yml down

# Show logs
logs:
	@if docker-compose ps -q | grep -q .; then \
		docker-compose logs -f; \
	elif docker-compose -f docker-compose.cpu.yml ps -q | grep -q .; then \
		docker-compose -f docker-compose.cpu.yml logs -f; \
	else \
		echo "No containers running"; \
	fi

# Run tests with dependency check (GPU mode)
test:
	@echo "Checking test dependencies..."
	@pip3 show requests > /dev/null 2>&1 || (echo "Installing test dependencies..." && pip3 install -r requirements-test.txt)
	@echo "Waiting for services to start..."
	@sleep 30
	python3 test_api.py

# Run tests CPU-only (no GPU required, but slower)
cpu-test:
	@echo "Starting CPU-only testing (no GPU required)..."
	@echo "Note: This will be slower than GPU mode but doesn't require NVIDIA drivers"
	@echo "Checking test dependencies..."
	@pip3 show requests > /dev/null 2>&1 || (echo "Installing test dependencies..." && pip3 install -r requirements-test.txt)
	@echo "Building CPU-only image..."
	docker-compose -f docker-compose.cpu.yml build
	@echo "Starting CPU-only services..."
	docker-compose -f docker-compose.cpu.yml up -d
	@echo "Waiting for CPU-only startup (120 seconds - first run may take longer for model download)..."
	@sleep 120
	@echo "Running tests..."
	python3 test_api.py || echo "Tests failed - check logs with 'make logs'"
	@echo "Stopping CPU-only services..."
	docker-compose -f docker-compose.cpu.yml down

# Clean up everything
clean:
	docker-compose down -v --remove-orphans
	docker-compose -f docker-compose.cpu.yml down -v --remove-orphans
	docker system prune -f

# Test GPU availability
gpu-test:
	@docker run --rm --gpus all nvidia/cuda:12.1-runtime-ubuntu22.04 nvidia-smi 2>/dev/null || echo "GPU not available - use CPU mode with 'make cpu-test'"

# Development mode (local Python environment)
dev:
	@echo "Starting development environment..."
	@echo "Make sure Ollama is running: ollama serve"
	@echo "Then run: python3 api_server.py"

# Build and start everything (GPU)
deploy: build up

# Build and start everything (CPU)
deploy-cpu: build-cpu up-cpu

# Full test cycle (GPU)
full-test: build up test

# Full test cycle (CPU)
full-test-cpu: build-cpu cpu-test

# Check Docker and NVIDIA setup
check-deps:
	@echo "Checking Docker..."
	docker --version
	@echo "Checking Docker Compose..."
	docker-compose --version
	@echo "Checking NVIDIA runtime (optional for CPU mode)..."
	@docker run --rm --gpus all nvidia/cuda:12.1-runtime-ubuntu22.04 nvidia-smi 2>/dev/null && echo "GPU available" || echo "GPU not available - use CPU mode"

# View resource usage
stats:
	docker stats

# Enter container shell
shell:
	@if docker-compose ps -q | grep -q .; then \
		docker-compose exec bakllava /bin/bash; \
	elif docker-compose -f docker-compose.cpu.yml ps -q | grep -q .; then \
		docker-compose -f docker-compose.cpu.yml exec bakllava /bin/bash; \
	else \
		echo "No containers running. Start with 'make up' or 'make up-cpu'"; \
	fi

# Test conversations (CPU mode)
test-conversation-cpu:
	@echo "Testing conversation functionality (CPU mode)..."
	@pip3 show requests > /dev/null 2>&1 || (echo "Installing test dependencies..." && pip3 install -r requirements-test.txt)
	docker-compose -f docker-compose.cpu.yml build
	docker-compose -f docker-compose.cpu.yml up -d
	@echo "Waiting for CPU services to start..."
	@sleep 120
	python3 test_conversation.py
	docker-compose -f docker-compose.cpu.yml down

# Test conversations (GPU mode)
test-conversation:
	@echo "Testing conversation functionality..."
	@pip3 show requests > /dev/null 2>&1 || (echo "Installing test dependencies..." && pip3 install -r requirements-test.txt)
	@echo "Waiting for services to start..."
	@sleep 30
	python3 test_conversation.py

# Quick start for CPU testing
quick-cpu-test:
	@echo "Quick CPU test (building if needed)..."
	@make build-cpu > /dev/null 2>&1 || true
	@make up-cpu
	@echo "Waiting 60 seconds for basic startup..."
	@sleep 60
	@curl -s http://localhost:8000/health || echo "Service not ready yet, try 'make cpu-test' for full test" 