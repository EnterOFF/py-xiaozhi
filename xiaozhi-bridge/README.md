# Xiaozhi Bridge

A proxy emulator that bridges SillyTavern (and similar applications) with the Xiaozhi AI service, emulating an ESP32 device.

## Overview

This project acts as a middleman between:
- **SillyTavern** (or any OpenAI-compatible client) 
- **Xiaozhi AI Service** (xiaozhi.me)

It emulates an ESP32 device, handles activation, and translates between OpenAI API format and Xiaozhi's proprietary protocol.

## Features

- 🎭 **ESP32 Emulation**: Generates realistic MAC addresses and device fingerprints
- 🔐 **Auto-Activation**: Built-in web UI for device activation via xiaozhi.me
- 🔄 **Protocol Translation**: Converts OpenAI API calls to Xiaozhi WebSocket/MQTT protocol
- 🎨 **Emotion Support**: Transmits emotion states between systems
- 🐳 **Docker Ready**: Single `docker-compose up` deployment
- 📡 **Dual Protocol**: Supports both WebSocket and MQTT connections

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  SillyTavern    │────▶│  Xiaozhi Bridge  │────▶│  Xiaozhi AI     │
│  (OpenAI API)   │     │  (ESP32 Emulator)│     │  (xiaozhi.me)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.10+ (for local development)
- Network access to `api.tenclass.net` and `xiaozhi.me`

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd xiaozhi-bridge
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Start the service:
```bash
docker-compose up -d
```

4. Access the activation UI:
```
http://localhost:8080
```

5. Follow the on-screen instructions to activate your device.

6. Configure SillyTavern to use:
```
API Endpoint: http://localhost:8000/v1
API Key: any-value (not used)
Model: xiaozhi-ai
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `XIAOZHI_OTA_URL` | `https://api.tenclass.net/xiaozhi/ota/` | Xiaozhi OTA server URL |
| `BRIDGE_HOST` | `0.0.0.0` | Bridge server bind address |
| `OPENAI_API_PORT` | `8000` | OpenAI-compatible API port |
| `WEB_UI_PORT` | `8080` | Web UI for activation port |
| `DEVICE_MAC` | (auto) | Override MAC address (optional) |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `PROTOCOL` | `websocket` | Connection protocol (websocket/mqtt) |

### Docker Compose Services

- **bridge**: Main proxy service
- **redis**: Session and state management (optional)
- **nginx**: Reverse proxy (optional, for production)

## API Reference

### OpenAI-Compatible Endpoints

#### POST `/v1/chat/completions`

Standard OpenAI chat completions endpoint.

**Request:**
```json
{
  "model": "xiaozhi-ai",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "stream": true
}
```

**Response (streaming):**
```
data: {"choices": [{"delta": {"content": "Hello"}}]}
data: {"choices": [{"delta": {"content": " there!"}}]}
data: [DONE]
```

#### POST `/v1/emotion`

Set device emotion state.

**Request:**
```json
{
  "emotion": "happy"
}
```

**Supported emotions:** `happy`, `sad`, `angry`, `surprised`, `neutral`, `listening`, `thinking`, `speaking`

#### GET `/v1/status`

Get device and connection status.

**Response:**
```json
{
  "activated": true,
  "connected": true,
  "mac_address": "00:11:22:33:44:55",
  "serial_number": "SN-ABC12345-001122334455",
  "protocol": "websocket",
  "emotion": "neutral"
}
```

### Web UI Endpoints

- `GET /` - Activation status and QR code
- `GET /activate` - Manual activation page
- `POST /activate/start` - Initiate activation process
- `GET /activate/status` - Poll activation status
- `POST /activate/reset` - Reset activation state

## How It Works

### 1. Device Emulation

The bridge generates a realistic ESP32-like identity:
- **MAC Address**: Either auto-generated from host interfaces or randomly created
- **Serial Number**: Format `SN-{MD5}-{MAC}` 
- **Device Fingerprint**: Stored in persistent storage (`/data/efuse.json`)
- **HMAC Key**: Generated during first run for activation signing

### 2. Activation Process

1. Bridge requests a challenge from Xiaozhi activation server
2. Web UI displays activation code to user
3. User logs into `xiaozhi.me` and enters the code
4. Bridge signs the challenge with HMAC-SHA256
5. Activation server validates and returns credentials
6. Bridge stores activation state and MQTT/WebSocket config

### 3. Message Flow

**User → Xiaozhi:**
```
SillyTavern → OpenAI API → Bridge → WebSocket → Xiaozhi AI
```

**Xiaozhi → User:**
```
Xiaozhi AI → WebSocket → Bridge → SSE Stream → SillyTavern
```

### 4. Emotion Handling

Emotions are transmitted bidirectionally:
- **Incoming**: Xiaozhi sends emotion updates → Bridge → SillyTavern (via custom headers/events)
- **Outgoing**: SillyTavern sets emotion → Bridge → Xiaozhi (protocol message)

## Development

### Local Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run in development mode
python -m src.main --dev
```

### Project Structure

```
xiaozhi-bridge/
├── src/
│   ├── main.py              # Application entry point
│   ├── api/                 # OpenAI-compatible API
│   │   ├── routes.py
│   │   └── schemas.py
│   ├── core/                # Core logic
│   │   ├── bridge.py        # Main bridge logic
│   │   ├── translator.py    # Protocol translation
│   │   └── emotions.py      # Emotion handling
│   ├── protocols/           # Xiaozhi protocols
│   │   ├── websocket.py
│   │   └── mqtt.py
│   ├── utils/               # Utilities
│   │   ├── device_id.py     # MAC/serial generation
│   │   ├── activator.py     # Activation logic
│   │   └── fingerprint.py   # Device fingerprinting
│   └── web/                 # Web UI
│       ├── static/
│       ├── templates/
│       └── server.py
├── data/                    # Persistent storage (mounted volume)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## Troubleshooting

### Activation Fails

1. Check network connectivity to `api.tenclass.net`
2. Verify system time is synchronized
3. Try resetting activation: `POST /activate/reset`
4. Check logs: `docker-compose logs bridge`

### Connection Drops

1. Verify WebSocket/MQTT credentials in activation response
2. Check firewall rules for outbound connections
3. Increase reconnect timeout in configuration

### SillyTavern Can't Connect

1. Ensure bridge is running: `curl http://localhost:8000/v1/status`
2. Verify correct endpoint URL in SillyTavern settings
3. Check CORS settings if running on different host

## Security Considerations

- 🔒 HMAC keys are stored securely in `/data/efuse.json`
- 🔒 All external connections use TLS (HTTPS/WSS/MQTTS)
- 🔒 Web UI should be protected in production (use nginx auth)
- ⚠️ Do not expose Web UI to public internet without authentication

## Limitations

- Audio streaming not supported (text-only mode)
- Some Xiaozhi-specific features may not translate perfectly
- Rate limiting depends on Xiaozhi service policies

## Contributing

Contributions welcome! Please read our contributing guidelines before submitting PRs.

## License

MIT License - See LICENSE file for details.

## Disclaimer

This project is for educational purposes only. Use at your own risk. Not affiliated with or endorsed by Xiaozhi/tenclass.net.

**Note:** This project was created with assistance from Qwen Coder.

## Support

- Issues: GitHub Issues
- Discussions: GitHub Discussions
- Documentation: Wiki

---

**Made with ❤️ for the AI community**
