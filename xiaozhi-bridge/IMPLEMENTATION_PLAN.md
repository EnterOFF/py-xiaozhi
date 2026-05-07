# Xiaozhi Bridge - Implementation Plan

## Project Overview

This document outlines the implementation plan for creating a proxy emulator that bridges SillyTavern (and similar applications) with the Xiaozhi AI service.

## Architecture Summary

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  SillyTavern    │────▶│  Xiaozhi Bridge  │────▶│  Xiaozhi AI     │
│  (OpenAI API)   │     │  (ESP32 Emulator)│     │  (xiaozhi.me)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Key Components Implemented

### 1. Device Identity (`src/utils/device_id.py`)
- **Purpose**: Generate and manage ESP32-like device identity
- **Features**:
  - MAC address generation (using real ESP32 OUI prefixes)
  - Serial number generation (format: `SN-{MD5}-{MAC}`)
  - HMAC key generation for activation signing
  - Persistent storage in `/data/efuse.json`
  - Support for MAC address override via environment variable

### 2. Device Activation (`src/utils/activator.py`)
- **Purpose**: Handle complete activation flow with xiaozhi.me
- **Features**:
  - Challenge request from activation server
  - HMAC-SHA256 signature generation
  - Activation submission with proper headers
  - Polling mechanism for activation status (60 attempts × 5 seconds)
  - Configuration retrieval after successful activation

### 3. Emotion Management (`src/utils/emotions.py`)
- **Purpose**: Translate emotions between systems
- **Features**:
  - Support for 8 emotion states
  - Translation to/from Xiaozhi protocol format
  - Emotion history tracking
  - Bidirectional emotion synchronization

### 4. WebSocket Protocol (`src/protocols/websocket.py`)
- **Purpose**: Maintain connection to Xiaozhi service
- **Features**:
  - Automatic reconnection with exponential backoff
  - Message send/receive handling
  - Text message support
  - Emotion update messages
  - Connection state management

### 5. Core Bridge Logic (`src/core/bridge.py`)
- **Purpose**: Main bridge connecting OpenAI API to Xiaozhi
- **Features**:
  - Session management
  - Message streaming
  - Emotion synchronization
  - Status reporting
  - Automatic connection on startup (if activated)

### 6. OpenAI-Compatible API (`src/api/`)
- **Purpose**: Provide SillyTavern-compatible endpoints
- **Endpoints**:
  - `POST /v1/chat/completions` - Chat with streaming support
  - `POST /v1/emotion` - Set device emotion
  - `GET /v1/status` - Get bridge status
  - `GET /v1/models` - List available models
  - `POST /v1/activate/*` - Activation management

### 7. Web UI (`src/web/`)
- **Purpose**: User-friendly activation interface
- **Pages**:
  - Dashboard with status overview
  - Activation page with code display
  - Success confirmation page
- **Features**:
  - Auto-refresh during activation
  - QR code support (future)
  - Responsive design

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `XIAOZHI_OTA_URL` | `https://api.tenclass.net/xiaozhi/ota/` | OTA server URL |
| `BRIDGE_HOST` | `0.0.0.0` | Server bind address |
| `OPENAI_API_PORT` | `8000` | API port |
| `WEB_UI_PORT` | `8080` | Web UI port |
| `DEVICE_MAC` | (auto) | Override MAC address |
| `LOG_LEVEL` | `INFO` | Logging level |
| `PROTOCOL` | `websocket` | Connection protocol |

### Docker Deployment

```bash
# Copy environment file
cp .env.example .env

# Start services
docker-compose up -d

# View logs
docker-compose logs -f bridge
```

## Activation Flow

1. **Start Bridge**: Container starts, generates device identity
2. **Request Code**: User visits `/activate`, gets activation code
3. **Enter Code**: User enters code on `xiaozhi.me`
4. **Poll Status**: Bridge polls for activation completion
5. **Save Config**: Activation credentials saved to `/data/efuse.json`
6. **Auto-Connect**: Bridge connects to Xiaozhi WebSocket server

## Message Flow

### User → Xiaozhi
```
SillyTavern 
  → POST /v1/chat/completions 
  → Bridge 
  → WebSocket 
  → Xiaozhi AI
```

### Xiaozhi → User
```
Xiaozhi AI 
  → WebSocket 
  → Bridge 
  → SSE Stream 
  → SillyTavern
```

## Security Considerations

1. **HMAC Keys**: Stored securely in `/data/efuse.json`
2. **TLS**: All external connections use HTTPS/WSS
3. **Volume Mounts**: Sensitive data persisted outside container
4. **Network Isolation**: Docker network separation

## Future Enhancements

- [ ] MQTT protocol support
- [ ] Audio streaming passthrough
- [ ] Multiple session support
- [ ] Rate limiting
- [ ] Metrics and monitoring
- [ ] Enhanced emotion support
- [ ] Plugin system

## Testing Checklist

- [ ] Device identity generation
- [ ] Activation flow (manual)
- [ ] WebSocket connection
- [ ] Message translation
- [ ] Emotion updates
- [ ] API compatibility with SillyTavern
- [ ] Docker deployment
- [ ] Reconnection logic

## Troubleshooting

### Common Issues

1. **Activation fails**
   - Check network connectivity to `api.tenclass.net`
   - Verify system time is synchronized
   - Try resetting: `POST /v1/activate/reset`

2. **Connection drops**
   - Check WebSocket URL in activation response
   - Verify firewall allows outbound WSS connections
   - Review logs: `docker-compose logs bridge`

3. **SillyTavern can't connect**
   - Verify endpoint: `http://host:8000/v1`
   - Check CORS settings if cross-origin
   - Test status endpoint: `curl http://localhost:8000/v1/status`

## Support

- Documentation: See README.md
- Issues: GitHub Issues
- Logs: `docker-compose logs -f`

---

**Status**: ✅ Implementation Complete
**Version**: 1.0.0
**Last Updated**: 2024
