# Camera Agent

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://hub.docker.com/)
[![Kubernetes](https://img.shields.io/badge/kubernetes-supported-green.svg)](https://kubernetes.io/)

A containerized system that transforms standard webcams into IP cameras with centralized management capabilities for MobileX environments. Provides seamless integration with Digital Twin Services, ROS2 networks, and AI services.

## 🏗️ System Architecture
#### update soon!!!
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Camera Agent   │──▶ │ Visibility Server│──▶│     WebUI       │
│  (GStreamer,    │    │  (Flask+TinyDB)  │    │   (jQuery)      │
│     kafka )     │    │                  │    │                 │
│ • RTSP Stream   │    │ • Agent Registry │    │ • Live Monitor  │
│ • FastAPI       │    │ • CRUD API       │    │ • Stream Control│
│ • Prometheus    │    │ • Prometheus     │    │ • Dashboard     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                  ┌──────────────────┐
                  │   PTP Server     │
                  │ (Time Sync)      │
                  └──────────────────┘
```

# Camera Agent based Streamer-Process-Service 3tier-Architecture

![Camera Agent 3계층 아키텍처](/docs/images/3tier-architecture.png)


## 🚧 Development Status

### Completed Features ✅
- Docker-based agent-server communication
- WebUI for agent monitoring and control
- RTSP streaming with GStreamer (only Box)
- KAFKA streaming (Box, ROS2, Omniverse)
- Agent registration and discovery

### In Progress 🔄
- Omniverse virtual camera synchronization
- PTP time synchronization reActivation
- Advanced Prometheus metrics
- Kubernetes deployment optimization

### Planned Features 📋
- Enhanced security features
- Performance optimization


## 🚀 Quick Start

Although pre-built images are provided, all Dockerfiles are also supplied so you can build and use them additionally as shown below.


```bash

# RTSP based Streaming 
docker run -d --rm \
    --network host \
    --name my-rtsp-camera-agent \
    --device /dev/video0:/dev/video0 \
    -e VISIBILITY_SERVER_URL="<YOUR visibility Server IP>" \
    -e AGENT_NAME="RTSP_Camera_Agent_01" \
    -e AGENT_PORT="8000" \
    -e STREAMING_METHOD="RTSP" \
    -e CAMERA_DEVICE_PATH="/dev/video0" \
    -e CAMERA_ID_OVERRIDE="a1b2c3d4-e5f6-7890-1234-567890abcdef" \
    -e CAMERA_NAME="MobileX_studio_(RTSP)" \
    -e CAMERA_TYPE="rgb" \
    -e CAMERA_ENVIRONMENT="real" \
    -e CAMERA_RESOLUTION="1280x720" \
    -e CAMERA_FPS="25" \
    -e CAMERA_LOCATION="MobileX_studio" \
    -e RTSP_SERVER_LISTEN_PORT="8554" \
    -e RTSP_MOUNT_POINT="/live_stream_01" \
    ttyy441/camera-agent:0.6.2

# KAFKA based Streaming  
docker run  --rm \
    --network host \
    --name my-kafka-camera-agent \
    --device /dev/video0:/dev/video0 \
    -e VISIBILITY_SERVER_URL="http://10.32.187.108:5111" \
    -e AGENT_NAME="Kafka_Camera_Agent_01" \
    -e AGENT_PORT="8000" \
    -e STREAMING_METHOD="KAFKA" \
    -e CAMERA_DEVICE_PATH="/dev/video0" \
    -e CAMERA_ID_OVERRIDE="kfk-cam-uuid-001" \
    -e CAMERA_NAME="공정라인 A 카메라 (Kafka)" \
    -e CAMERA_TYPE="rgb" \
    -e CAMERA_ENVIRONMENT="real" \
    -e CAMERA_RESOLUTION="1280x720" \
    -e CAMERA_FPS="20" \
    -e CAMERA_LOCATION="공정라인 A 위" \
    -e KAFKA_TOPIC="camera-agent-01" \
    -e KAFKA_BOOTSTRAP_SERVERS="10.79.1.1:9094" \
    ttyy441/camera-agent:0.6.1

```

### Local Development
```bash
# Clone repository
git clone https://github.com/SmartX-Team/camera-agent.git
cd camera-agent


### Individual Service Deployment
```bash
# Camera Agent
cd Agent
docker build -t camera-agent:latest .
docker run -d --name camera-agent \
  --device=/dev/video0:/dev/video0 \
  -p 8554:8554 -p 8000:8000 \
  camera-agent:latest

# Visibility Server
cd Backend
docker build -t visibility-server:latest .
docker run -d --name visibility-server \
  -p 5000:5000 \
  visibility-server:latest

# WebUI
cd WebUI
docker build -t camera-webui:latest .
docker run -d --name camera-webui \
  -p 3000:3000 \
  camera-webui:latest
```

## 📦 Core Components

### 🎥 Camera Agent (sub folder: fastapi_agent)
**Technology Stack:** FastAPI, GStreamer, Prometheus Client
**Purpose:** Transforms webcams into RTSP-streamable IP cameras with real-time monitoring

#### Key Features
- **RTSP/KAFKA Streaming**: GStreamer-based pipeline for multi-client camera access
- **Dynamic Control**: RESTful API for stream start/stop operations
- **Time Synchronization**: PTP protocol support (currently disabled for stability)
- **Metrics Export**: Prometheus-compatible system metrics
- **Auto-Registration**: Automatic registration with Visibility Server

#### API Endpoints
```
POST   /start_stream     # Start camera streaming
POST   /stop_stream      # Stop camera streaming
GET    /health           # Health check endpoint
GET    /metrics          # Prometheus metrics
```

#### Configuration
```yaml
# Agent configuration
camera:
  device: "/dev/video0"
  resolution: "1920x1080"
  framerate: 30
  codec: "h264"

rtsp:
  port: 8554
  path: "/stream"

api:
  port: 8000
  host: "0.0.0.0"
```

### 🖥️ Visibility Server (Backend)
**Technology Stack:** Flask, TinyDB, CORS Middleware
**Purpose:** Centralized agent state management and WebUI API provider

#### Key Features
- **Agent Registry**: Automatic agent discovery and registration
- **Database Management**: TinyDB-based lightweight data persistence
- **Stream Control**: Remote agent control via proxy API
- **Prometheus Integration**: Metrics aggregation and forwarding
- **Duplicate Prevention**: IP-based duplicate agent filtering

#### Database Schema
```json
{
  "agent_id": "string",
  "ip_address": "string", 
  "rtsp_port": "integer",
  "agent_port": "integer",
  "status": "string",
  "last_seen": "timestamp",
  "metadata": {
    "hostname": "string",
    "os": "string",
    "camera_info": "object"
  }
}
```

#### API Endpoints
```
POST   /register_agent           # Agent registration
GET    /agents                   # List all agents
GET    /agents/{id}              # Get agent details
POST   /agents/{id}/control      # Control agent stream
GET    /prometheus/metrics       # Aggregated metrics
```

### 🌐 WebUI (light)
**Technology Stack:** jQuery, Bootstrap, Chart.js
**Purpose:** Real-time monitoring and control interface

#### Features
- **Live Dashboard**: Real-time agent status monitoring
- **Stream Control**: One-click stream start/stop functionality
- **Metrics Visualization**: System performance charts
- **Responsive Design**: Mobile-friendly interface
- **CORS Support**: Cross-origin API access


![Web-UI](/docs/images/agent-ui.png)


### AI-service-visibility 
While the functionality is supported, it only provides REST API support and is not yet officially documented. It acts as a server that manages metadata for applying desired camera sources to specific AI services, based on Redis.


### ⏱️ PTP Server
**Technology Stack:** Linux PTP, Docker
**Purpose:** Network time synchronization for multi-agent deployments

> **Note:** Currently implemented but disabled pending stability validation


### Health Checks
```bash
# Agent health
curl http://localhost:8000/health

# Server health  
curl http://localhost:5000/health

# Stream availability
curl -I rtsp://localhost:8554/stream
```

## 🔧 Configuration

### Environment Variables
```bash
# Camera Agent
CAMERA_DEVICE=/dev/video0
RTSP_PORT=8554
API_PORT=8000
VISIBILITY_SERVER_URL=http://localhost:5000
PROMETHEUS_PORT=8001

# Visibility Server
DB_PATH=/app/data/agents.json
CORS_ORIGINS=http://localhost:3000
PROMETHEUS_ENDPOINT=http://localhost:9090

# WebUI
API_BASE_URL=http://localhost:5000
REFRESH_INTERVAL=5000
ENABLE_METRICS=true
```

### Camera Configuration
```json
{
  "camera": {
    "device": "/dev/video0",
    "width": 1920,
    "height": 1080,
    "framerate": 30,
    "format": "YUYV",
    "buffers": 4
  },
  "encoding": {
    "codec": "h264",
    "bitrate": 2000000,
    "keyframe_interval": 30
  },
  "rtsp": {
    "port": 8554,
    "path": "/stream",
    "authentication": false
  }
}
```


### API Documentation
- **Swagger UI**: Available at `http://localhost:8000/docs`


### Quick Links 


## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **GIST NetAI Lab**: Research collaboration and support

---

**Note**: This project is part of the larger MobileX Digital Twin ecosystem. For comprehensive integration examples and advanced use cases, refer to the [Digital Twin Project](https://github.com/songinyong/).