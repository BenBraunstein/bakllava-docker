# Bakllava 7B Docker API Server

A Docker-based API server for the Bakllava 7B vision-language model with NVIDIA GPU acceleration support. This setup provides a FastAPI interface for interacting with the model using text prompts, single images, and video frames.

## Features

- 🚀 **Bakllava 7B Model**: Latest multimodal vision-language model
- 🐳 **Docker Support**: Complete containerized solution
- 🎮 **NVIDIA GPU Acceleration**: Optimized for CUDA-enabled GPUs
- 🌐 **REST API**: FastAPI-based web interface
- 📸 **Multi-Input Support**: Text, images, and video frame sequences
- 📊 **Health Monitoring**: Built-in health checks and monitoring
- 🔄 **Auto-Model Download**: Automatic model pulling on first run

## Requirements

### Hardware
- NVIDIA GPU with CUDA support
- Minimum 8GB GPU VRAM (recommended for optimal performance)
- 16GB+ system RAM

### Software
- Docker Engine 20.10+
- Docker Compose v2.0+
- NVIDIA Container Toolkit
- NVIDIA GPU drivers (latest)

## Quick Start

### 1. Install NVIDIA Container Toolkit

#### Ubuntu/Debian:
```bash
# Configure the repository
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Update and install
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### 2. Clone and Build

```bash
git clone https://github.com/yourusername/bakllava-docker.git
cd bakllava-docker

# Build and start with GPU support
docker-compose up --build
```

### 3. Verify Installation

```bash
# Check container health
docker-compose ps

# Check API health
curl http://localhost:8000/health
```

## API Usage

The server provides three main endpoints:

### Text-Only Prompts
```bash
curl -X POST "http://localhost:8000/api/text" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain the concept of artificial intelligence",
    "temperature": 0.7,
    "max_tokens": 1024
  }'
```

### Single Image Analysis
```bash
curl -X POST "http://localhost:8000/api/image" \
  -F "prompt=What do you see in this image?" \
  -F "temperature=0.7" \
  -F "max_tokens=1024" \
  -F "image=@/path/to/your/image.jpg"
```

### Video Frame Analysis
```bash
curl -X POST "http://localhost:8000/api/video" \
  -F "prompt=Describe what happens in this video sequence" \
  -F "frame_rate=1.0" \
  -F "temperature=0.7" \
  -F "max_tokens=1024" \
  -F "frames=@/path/to/frame1.jpg" \
  -F "frames=@/path/to/frame2.jpg" \
  -F "frames=@/path/to/frame3.jpg"
```

### Interactive API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation with Swagger UI.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `0.0.0.0` | Ollama service host |
| `OLLAMA_PORT` | `11434` | Ollama service port |
| `CUDA_VISIBLE_DEVICES` | `all` | GPU devices to use |

### Model Configuration

The container automatically downloads the Bakllava model on first startup. This process may take 10-20 minutes depending on your internet connection.

### Performance Tuning

For optimal performance on your specific hardware:

1. **Memory Management**: Adjust `max_tokens` based on available GPU memory
2. **Concurrent Requests**: Modify the FastAPI server configuration in `api_server.py`
3. **Model Parameters**: Tune `temperature` and other generation parameters

## Development

### Local Development Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start Ollama (separate terminal)
ollama serve

# Pull model
ollama pull bakllava

# Run development server
python api_server.py
```

### Building Custom Images

#### Using GitHub Container Registry (Recommended)

```bash
# Build with GitHub Container Registry tag
docker build -t ghcr.io/your-github-username/bakllava-docker:latest .

# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u your-github-username --password-stdin

# Push to GitHub Container Registry
docker push ghcr.io/your-github-username/bakllava-docker:latest
```

#### Or using Docker Hub

```bash
# Build with custom tag
docker build -t your-registry/bakllava:latest .

# Push to registry
docker push your-registry/bakllava:latest
```

## Deployment

### Automated GitHub Container Registry

This project includes a GitHub Actions workflow that automatically builds and pushes Docker images to GitHub Container Registry when you push to the main branch.

**Setup Steps:**
1. Push your code to GitHub
2. Go to your repository → Settings → Actions → General 
3. Enable "Read and write permissions" for GITHUB_TOKEN
4. The workflow will automatically build and push images on every commit to main

**Your image will be available at:**
```
ghcr.io/your-github-username/bakllava-docker:latest
```

### Production Deployment

For production deployment, consider:

1. **Resource Limits**: Set appropriate CPU/memory limits
2. **Scaling**: Use multiple replicas behind a load balancer
3. **Security**: Implement authentication and rate limiting
4. **Monitoring**: Add logging and metrics collection
5. **Persistence**: Ensure model data is properly persisted

### Unraid Server Deployment

For Unraid servers:

1. Install the Community Applications plugin
2. Add the NVIDIA plugin for GPU support
3. Use the provided `docker-compose.yml` or create a custom template
4. Configure GPU passthrough in Unraid settings

### Example Unraid Template

```xml
<?xml version="1.0"?>
<Container version="2">
  <Name>bakllava-api</Name>
  <Repository>ghcr.io/your-github-username/bakllava-docker:latest</Repository>
  <Registry/>
  <Network>bridge</Network>
  <Privileged>false</Privileged>
  <Support/>
  <Project/>
  <Overview>Bakllava 7B Vision-Language Model API Server</Overview>
  <Category>AI:</Category>
  <WebUI>http://[IP]:[PORT:8000]/docs</WebUI>
  <TemplateURL/>
  <Icon/>
  <ExtraParams>--runtime=nvidia</ExtraParams>
  <PostArgs/>
  <CPUset/>
  <DateInstalled/>
  <DonateText/>
  <DonateLink/>
  <Description>Bakllava 7B Vision-Language Model with FastAPI interface</Description>
  <Networking>
    <Mode>bridge</Mode>
    <Publish>
      <Port>
        <HostPort>8000</HostPort>
        <ContainerPort>8000</ContainerPort>
        <Protocol>tcp</Protocol>
      </Port>
      <Port>
        <HostPort>11434</HostPort>
        <ContainerPort>11434</ContainerPort>
        <Protocol>tcp</Protocol>
      </Port>
    </Publish>
  </Networking>
  <Data>
    <Volume>
      <HostDir>/mnt/user/appdata/bakllava</HostDir>
      <ContainerDir>/root/.ollama</ContainerDir>
      <Mode>rw</Mode>
    </Volume>
  </Data>
  <Environment>
    <Variable>
      <Value>all</Value>
      <Name>CUDA_VISIBLE_DEVICES</Name>
      <Mode/>
    </Variable>
  </Environment>
  <Labels/>
  <Config Name="API Port" Target="8000" Default="8000" Mode="tcp" Description="FastAPI server port" Type="Port" Display="always" Required="true" Mask="false"/>
  <Config Name="Ollama Port" Target="11434" Default="11434" Mode="tcp" Description="Ollama service port" Type="Port" Display="always" Required="true" Mask="false"/>
  <Config Name="Model Data" Target="/root/.ollama" Default="/mnt/user/appdata/bakllava" Mode="rw" Description="Model storage directory" Type="Path" Display="always" Required="true" Mask="false"/>
  <Config Name="GPU Devices" Target="CUDA_VISIBLE_DEVICES" Default="all" Description="GPU devices to use" Type="Variable" Display="always" Required="false" Mask="false"/>
</Container>
```

## Troubleshooting

### Common Issues

1. **GPU Not Detected**
   ```bash
   # Verify NVIDIA runtime
   docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
   ```

2. **Model Download Fails**
   ```bash
   # Check internet connectivity and disk space
   docker-compose logs bakllava
   ```

3. **Out of Memory Errors**
   ```bash
   # Reduce max_tokens or use CPU-only mode
   # Check GPU memory: nvidia-smi
   ```

4. **Container Won't Start**
   ```bash
   # Check logs
   docker-compose logs bakllava
   
   # Verify dependencies
   docker --version
   docker-compose --version
   nvidia-smi
   ```

### Performance Optimization

- **GPU Memory**: Monitor with `nvidia-smi` and adjust `max_tokens`
- **Concurrent Requests**: Limit based on GPU memory capacity
- **Model Caching**: Ensure persistent volume for model data
- **Network**: Use high-speed storage for model files

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Ollama](https://ollama.ai/) for the excellent model serving platform
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [NVIDIA](https://developer.nvidia.com/) for CUDA and container toolkit
- [Bakllava Team](https://github.com/SkunkworksAI/BakLLaVA) for the vision-language model