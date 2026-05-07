"""
Main application entry point.
Initializes and runs the Xiaozhi Bridge server.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .utils import DeviceIdentity
from .core import XiaozhiBridge
from .api.routes import router as api_router, set_bridge
from .web.server import setup_web_ui

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Global bridge instance
bridge: XiaozhiBridge = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global bridge
    
    logger.info("Starting Xiaozhi Bridge...")
    
    # Initialize device identity
    data_dir = "/data"
    override_mac = os.getenv('DEVICE_MAC') or None
    
    identity = DeviceIdentity(data_dir)
    identity.initialize(override_mac)
    
    logger.info(f"Device MAC: {identity.mac_address}")
    logger.info(f"Device Serial: {identity.serial_number}")
    
    # Initialize bridge
    ota_url = os.getenv('XIAOZHI_OTA_URL', 'https://api.tenclass.net/xiaozhi/ota/')
    protocol = os.getenv('PROTOCOL', 'websocket')
    
    bridge = XiaozhiBridge(
        ota_url=ota_url,
        device_identity=identity,
        protocol=protocol
    )
    
    # Set bridge in API routes
    set_bridge(bridge)
    
    # Auto-connect if already activated
    if identity.is_activated():
        logger.info("Device is activated, attempting to connect...")
        connected = await bridge.connect()
        if connected:
            logger.info("Successfully connected to Xiaozhi service")
        else:
            logger.warning("Failed to connect to Xiaozhi service")
    else:
        logger.info("Device not activated. Visit /activate to activate.")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Xiaozhi Bridge...")
    if bridge:
        await bridge.cleanup()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="Xiaozhi Bridge",
        description="ESP32 Emulator for SillyTavern - Bridge to Xiaozhi AI",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API router
    app.include_router(api_router)
    
    # Setup Web UI
    setup_web_ui(app, bridge)
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    host = os.getenv('BRIDGE_HOST', '0.0.0.0')
    port = int(os.getenv('OPENAI_API_PORT', '8000'))
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=False,
        log_level=log_level.lower()
    )
