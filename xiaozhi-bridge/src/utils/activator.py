"""
Device activation utilities for Xiaozhi service.
Handles the complete activation flow with xiaozhi.me
"""

import asyncio
import hashlib
import hmac
import json
import logging
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)


class DeviceActivator:
    """Handles device activation with Xiaozhi service."""
    
    def __init__(self, ota_url: str, device_identity):
        self.ota_url = ota_url.rstrip('/')
        self.identity = device_identity
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def request_challenge(self) -> Optional[str]:
        """Request activation challenge from server."""
        url = f"{self.ota_url}activate/challenge"
        
        headers = {
            "Device-Id": self.identity.mac_address,
            "Client-Id": self.identity.client_id,
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.client.post(url, headers=headers, json={})
            response.raise_for_status()
            data = response.json()
            
            challenge = data.get('challenge')
            if challenge:
                logger.info(f"Received activation challenge: {challenge[:8]}...")
                return challenge
            
            logger.error("No challenge in response")
            return None
            
        except Exception as e:
            logger.error(f"Failed to request challenge: {e}")
            return None
    
    def generate_hmac_signature(self, challenge: str) -> str:
        """Generate HMAC-SHA256 signature for challenge."""
        hmac_key = self.identity.get_hmac_key()
        signature = hmac.new(
            hmac_key.encode(),
            challenge.encode(),
            hashlib.sha256
        ).hexdigest()
        
        logger.debug(f"Generated HMAC signature for challenge")
        return signature
    
    async def submit_activation(
        self, 
        challenge: str, 
        hmac_signature: str
    ) -> Optional[Dict[str, Any]]:
        """Submit activation credentials to server."""
        url = f"{self.ota_url}activate"
        
        headers = {
            "Activation-Version": "2",
            "Device-Id": self.identity.mac_address,
            "Client-Id": self.identity.client_id,
            "Content-Type": "application/json"
        }
        
        payload = {
            "Payload": {
                "algorithm": "hmac-sha256",
                "serial_number": self.identity.serial_number,
                "challenge": challenge,
                "hmac": hmac_signature,
            }
        }
        
        try:
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            logger.info("Activation submitted successfully")
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during activation: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Failed to submit activation: {e}")
            return None
    
    async def poll_activation_status(
        self, 
        max_attempts: int = 60, 
        delay_seconds: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Poll for activation status after user enters code on xiaozhi.me.
        
        Returns activation config when successful, None on timeout/failure.
        """
        logger.info(f"Polling activation status (max {max_attempts} attempts)")
        
        for attempt in range(max_attempts):
            try:
                # Request new challenge each time
                challenge = await self.request_challenge()
                if not challenge:
                    await asyncio.sleep(delay_seconds)
                    continue
                
                # Generate signature
                signature = self.generate_hmac_signature(challenge)
                
                # Submit activation
                result = await self.submit_activation(challenge, signature)
                
                if result and result.get('activated'):
                    logger.info("Activation successful!")
                    return result
                
                logger.debug(f"Attempt {attempt + 1}/{max_attempts}: waiting...")
                await asyncio.sleep(delay_seconds)
                
            except Exception as e:
                logger.error(f"Error during polling attempt {attempt + 1}: {e}")
                await asyncio.sleep(delay_seconds)
        
        logger.warning("Activation polling timed out")
        return None
    
    async def get_activation_config(self) -> Optional[Dict[str, Any]]:
        """
        Get current activation configuration from OTA server.
        Called after successful activation to retrieve MQTT/WebSocket details.
        """
        url = f"{self.ota_url}"
        
        headers = {
            "Device-Id": self.identity.mac_address,
            "Client-Id": self.identity.client_id,
            "Content-Type": "application/json"
        }
        
        body = {
            "version": "1.0.0",
            "flash_size": "4MB",
            "device_id": self.identity.mac_address
        }
        
        try:
            response = await self.client.post(url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
            
            logger.info("Retrieved activation configuration")
            return data
            
        except Exception as e:
            logger.error(f"Failed to get activation config: {e}")
            return None
    
    async def activate_with_user_code(self) -> tuple[bool, Optional[str]]:
        """
        Complete activation flow that returns a user code to display.
        
        Returns: (success: bool, user_code: Optional[str])
        """
        # Request initial challenge
        challenge = await self.request_challenge()
        if not challenge:
            return False, None
        
        # Extract user code from challenge (usually last 6-8 chars)
        # Format varies, but typically like "ACTIVATE-XXXXXX" or just "XXXXXX"
        user_code = challenge.split('-')[-1] if '-' in challenge else challenge
        user_code = user_code[:8].upper()  # Take first 8 chars max
        
        logger.info(f"User should enter code on xiaozhi.me: {user_code}")
        
        return True, user_code
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
