"""
WebSocket protocol implementation for Xiaozhi service.
Handles bidirectional communication with Xiaozhi AI servers.
"""

import asyncio
import json
import logging
from typing import Optional, Callable, Any
import websockets
from websockets.client import WebSocketClientProtocol

logger = logging.getLogger(__name__)


class XiaozhiWebSocket:
    """Manages WebSocket connection to Xiaozhi service."""
    
    def __init__(
        self, 
        ws_url: str,
        on_message: Optional[Callable[[dict], Any]] = None,
        on_connect: Optional[Callable[[], Any]] = None,
        on_disconnect: Optional[Callable[[], Any]] = None
    ):
        self.ws_url = ws_url
        self.on_message = on_message
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        
        self._ws: Optional[WebSocketClientProtocol] = None
        self._connected = False
        self._receive_task: Optional[asyncio.Task] = None
        self._reconnect_delay = 5.0
        self._max_reconnect_attempts = 10
    
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._connected and self._ws is not None
    
    async def connect(self) -> bool:
        """Establish WebSocket connection."""
        try:
            logger.info(f"Connecting to WebSocket: {self.ws_url}")
            
            self._ws = await websockets.connect(
                self.ws_url,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10
            )
            
            self._connected = True
            logger.info("WebSocket connected successfully")
            
            if self.on_connect:
                await self._safe_callback(self.on_connect)
            
            # Start receive loop
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect WebSocket: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        self._connected = False
        
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        if self._ws:
            await self._ws.close()
            self._ws = None
        
        logger.info("WebSocket disconnected")
        
        if self.on_disconnect:
            await self._safe_callback(self.on_disconnect)
    
    async def send(self, message: dict) -> bool:
        """Send JSON message through WebSocket."""
        if not self.is_connected or not self._ws:
            logger.warning("Cannot send: WebSocket not connected")
            return False
        
        try:
            json_message = json.dumps(message)
            await self._ws.send(json_message)
            logger.debug(f"Sent: {json_message[:100]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    async def send_text(self, text: str) -> bool:
        """Send text message (user input)."""
        message = {
            "type": "listen",
            "state": "start",
            "mode": "text"
        }
        
        if not await self.send(message):
            return False
        
        # Send the actual text
        text_message = {
            "type": "audit",
            "text": text
        }
        
        return await self.send(text_message)
    
    async def send_emotion(self, emotion: str) -> bool:
        """Send emotion update."""
        message = {
            "type": "llm",
            "emotion": emotion
        }
        return await self.send(message)
    
    async def _receive_loop(self) -> None:
        """Continuous loop to receive messages."""
        while self._connected and self._ws:
            try:
                message = await self._ws.recv()
                
                # Parse JSON
                try:
                    data = json.loads(message)
                    logger.debug(f"Received: {str(data)[:100]}...")
                    
                    if self.on_message:
                        await self._safe_callback(self.on_message, data)
                        
                except json.JSONDecodeError:
                    logger.warning(f"Received non-JSON message: {message[:100]}")
                    
            except websockets.ConnectionClosed:
                logger.info("WebSocket connection closed")
                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in receive loop: {e}")
                break
        
        self._connected = False
    
    async def _safe_callback(self, callback: Callable, *args) -> None:
        """Safely execute callback without crashing the loop."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            logger.error(f"Callback error: {e}")
    
    async def reconnect(self) -> bool:
        """Attempt to reconnect."""
        logger.info(f"Attempting to reconnect (delay: {self._reconnect_delay}s)")
        await asyncio.sleep(self._reconnect_delay)
        return await self.connect()
