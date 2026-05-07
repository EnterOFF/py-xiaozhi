"""
Core bridge logic.
Connects OpenAI API to Xiaozhi service.
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager

from ..utils import DeviceIdentity, DeviceActivator, EmotionManager
from ..protocols import XiaozhiWebSocket

logger = logging.getLogger(__name__)


class BridgeSession:
    """Represents a single chat session with Xiaozhi."""
    
    def __init__(self, session_id: str, ws: XiaozhiWebSocket, emotion_manager: EmotionManager):
        self.session_id = session_id
        self.ws = ws
        self.emotion_manager = emotion_manager
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.response_chunks: list[str] = []
    
    async def send_message(self, text: str) -> None:
        """Send user message to Xiaozhi."""
        await self.ws.send_text(text)
        logger.info(f"Sent message to Xiaozhi: {text[:50]}...")
    
    async def set_emotion(self, emotion: str) -> bool:
        """Set emotion for the session."""
        if self.emotion_manager.set_emotion(emotion):
            xiaozhi_msg = self.emotion_manager.translate_to_xiaozhi(emotion)
            if xiaozhi_msg:
                await self.ws.send(xiaozhi_msg)
            return True
        return False
    
    async def wait_for_response(self, timeout: float = 60.0) -> AsyncGenerator[str, None]:
        """Wait for and stream response from Xiaozhi."""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            try:
                remaining = timeout - (asyncio.get_event_loop().time() - start_time)
                if remaining <= 0:
                    break
                
                chunk = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=remaining
                )
                yield chunk
                
            except asyncio.TimeoutError:
                break
    
    async def add_response_chunk(self, chunk: str) -> None:
        """Add a chunk of response text."""
        self.response_chunks.append(chunk)
        await self.message_queue.put(chunk)
    
    def get_full_response(self) -> str:
        """Get complete response text."""
        return ''.join(self.response_chunks)


class XiaozhiBridge:
    """Main bridge connecting OpenAI API to Xiaozhi service."""
    
    def __init__(
        self,
        ota_url: str,
        device_identity: DeviceIdentity,
        protocol: str = "websocket"
    ):
        self.ota_url = ota_url
        self.identity = device_identity
        self.protocol_type = protocol
        
        self.activator = DeviceActivator(ota_url, device_identity)
        self.emotion_manager = EmotionManager()
        
        self._ws: Optional[XiaozhiWebSocket] = None
        self._session: Optional[BridgeSession] = None
        self._ws_config: Optional[Dict[str, Any]] = None
        self._connected = False
    
    @property
    def is_connected(self) -> bool:
        """Check if bridge is connected to Xiaozhi."""
        return self._connected and self._ws is not None and self._ws.is_connected
    
    @property
    def current_emotion(self) -> str:
        """Get current emotion."""
        return self.emotion_manager.current_emotion.value
    
    async def activate(self) -> tuple[bool, Optional[str]]:
        """
        Start activation process.
        
        Returns: (success, user_code)
        """
        if self.identity.is_activated():
            logger.info("Device already activated")
            return True, None
        
        success, user_code = await self.activator.activate_with_user_code()
        return success, user_code
    
    async def poll_activation(self) -> Optional[Dict[str, Any]]:
        """Poll for activation completion."""
        result = await self.activator.poll_activation_status()
        
        if result:
            self.identity.set_activated(True)
            self._ws_config = result
            logger.info("Activation completed successfully")
        
        return result
    
    async def connect(self) -> bool:
        """Connect to Xiaozhi service."""
        if not self.identity.is_activated():
            logger.error("Device not activated")
            return False
        
        # Get config if not cached
        if not self._ws_config:
            self._ws_config = await self.activator.get_activation_config()
            if not self._ws_config:
                logger.error("Failed to get connection config")
                return False
        
        # Extract WebSocket URL
        ws_url = self._ws_config.get('websocket_url') or self._ws_config.get('ws_url')
        if not ws_url:
            logger.error("No WebSocket URL in config")
            return False
        
        # Create WebSocket connection
        self._ws = XiaozhiWebSocket(
            ws_url=ws_url,
            on_message=self._on_message,
            on_connect=self._on_connect,
            on_disconnect=self._on_disconnect
        )
        
        connected = await self._ws.connect()
        if connected:
            self._connected = True
            self._session = BridgeSession(
                session_id="default",
                ws=self._ws,
                emotion_manager=self.emotion_manager
            )
        
        return connected
    
    async def disconnect(self) -> None:
        """Disconnect from Xiaozhi service."""
        if self._ws:
            await self._ws.disconnect()
        self._connected = False
        self._session = None
    
    async def send_message(self, text: str) -> None:
        """Send message to Xiaozhi."""
        if not self._session:
            raise RuntimeError("No active session")
        
        await self._session.send_message(text)
    
    async def set_emotion(self, emotion: str) -> bool:
        """Set emotion."""
        if not self._session:
            return False
        
        return await self._session.set_emotion(emotion)
    
    async def _on_message(self, data: dict) -> None:
        """Handle incoming message from Xiaozhi."""
        logger.debug(f"Received message: {data}")
        
        # Check for emotion update
        if data.get('type') == 'llm' and 'emotion' in data:
            emotion = self.emotion_manager.translate_from_xiaozhi(data)
            if emotion:
                logger.info(f"Emotion updated: {emotion}")
        
        # Check for response text
        if 'text' in data or 'content' in data:
            text = data.get('text') or data.get('content', '')
            if text and self._session:
                await self._session.add_response_chunk(text)
    
    def _on_connect(self) -> None:
        """Handle WebSocket connection."""
        logger.info("Connected to Xiaozhi service")
    
    def _on_disconnect(self) -> None:
        """Handle WebSocket disconnection."""
        logger.info("Disconnected from Xiaozhi service")
        self._connected = False
    
    def get_status(self) -> dict:
        """Get bridge status."""
        return {
            'activated': self.identity.is_activated(),
            'connected': self.is_connected,
            'mac_address': self.identity.mac_address,
            'serial_number': self.identity.serial_number,
            'protocol': self.protocol_type,
            'emotion': self.current_emotion
        }
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        await self.disconnect()
        await self.activator.close()
