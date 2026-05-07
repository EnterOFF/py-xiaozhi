"""
Device ID and MAC address generation utilities.
Emulates ESP32 device identity.
"""

import hashlib
import json
import os
import random
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DeviceIdentity:
    """Manages ESP32-like device identity including MAC address and serial number."""
    
    def __init__(self, data_dir: str = "/data"):
        self.data_dir = Path(data_dir)
        self.efuse_file = self.data_dir / "efuse.json"
        self.mac_address: Optional[str] = None
        self.serial_number: Optional[str] = None
        self.hmac_key: Optional[str] = None
        self.client_id: Optional[str] = None
        
    def initialize(self, override_mac: Optional[str] = None) -> None:
        """Initialize device identity, loading from storage or generating new."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Try to load existing identity
        if self.efuse_file.exists():
            self._load_identity()
            logger.info(f"Loaded existing device identity: {self.mac_address}")
            return
        
        # Generate new identity
        self._generate_identity(override_mac)
        self._save_identity()
        logger.info(f"Generated new device identity: {self.mac_address}")
    
    def _load_identity(self) -> None:
        """Load identity from efuse file."""
        try:
            with open(self.efuse_file, 'r') as f:
                data = json.load(f)
            
            self.mac_address = data.get('mac_address')
            self.serial_number = data.get('serial_number')
            self.hmac_key = data.get('hmac_key')
            self.client_id = data.get('client_id')
        except Exception as e:
            logger.error(f"Failed to load identity: {e}")
            raise
    
    def _save_identity(self) -> None:
        """Save identity to efuse file."""
        data = {
            'mac_address': self.mac_address,
            'serial_number': self.serial_number,
            'hmac_key': self.hmac_key,
            'client_id': self.client_id,
            'activation_status': False,
            'activation_time': None
        }
        
        with open(self.efuse_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _generate_identity(self, override_mac: Optional[str] = None) -> None:
        """Generate new device identity."""
        # Generate or use provided MAC address
        if override_mac:
            self.mac_address = override_mac.upper()
        else:
            self.mac_address = self._generate_mac()
        
        # Generate client ID (UUID-like format)
        self.client_id = self._generate_client_id()
        
        # Generate HMAC key (random 32-byte hex)
        self.hmac_key = os.urandom(32).hex()
        
        # Generate serial number: SN-{MD5 first 8 chars}-{MAC without colons}
        mac_hash = hashlib.md5(self.mac_address.encode()).hexdigest()[:8].upper()
        mac_clean = self.mac_address.replace(':', '')
        self.serial_number = f"SN-{mac_hash}-{mac_clean}"
    
    def _generate_mac(self) -> str:
        """
        Generate a realistic ESP32-like MAC address.
        ESP32 MACs typically start with 24:6F:28 or similar OUI.
        We'll generate a valid unicast MAC with proper formatting.
        """
        # Use common ESP32 OUI prefixes or generate random valid MAC
        esp32_ouis = [
            "24:6F:28",  # Espressif Inc.
            "30:AE:A4",  # Espressif Inc.
            "5C:CF:7F",  # Espressif Inc.
            "84:F7:03",  # Espressif Inc.
        ]
        
        # Randomly select an OUI or generate random
        if random.random() > 0.3:  # 70% chance to use real ESP32 OUI
            oui = random.choice(esp32_ouis)
            remaining = ':'.join([
                f"{random.randint(0, 255):02X}"
                for _ in range(3)
            ])
            mac = f"{oui}:{remaining}"
        else:
            # Generate random valid unicast MAC
            # First byte must be even (unicast) and not 0xFF (broadcast)
            first_byte = random.randint(0, 254) & 0xFE  # Ensure even
            mac_parts = [f"{first_byte:02X}"]
            mac_parts.extend([f"{random.randint(0, 255):02X}" for _ in range(5)])
            mac = ':'.join(mac_parts)
        
        return mac
    
    def _generate_client_id(self) -> str:
        """Generate a unique client ID."""
        import uuid
        return str(uuid.uuid4())
    
    def get_hmac_key(self) -> str:
        """Get the HMAC key for signing."""
        if not self.hmac_key:
            raise ValueError("HMAC key not initialized")
        return self.hmac_key
    
    def is_activated(self) -> bool:
        """Check if device is activated."""
        if not self.efuse_file.exists():
            return False
        
        try:
            with open(self.efuse_file, 'r') as f:
                data = json.load(f)
            return data.get('activation_status', False)
        except:
            return False
    
    def set_activated(self, activated: bool = True) -> None:
        """Set activation status."""
        if not self.efuse_file.exists():
            self._save_identity()
        
        with open(self.efuse_file, 'r') as f:
            data = json.load(f)
        
        data['activation_status'] = activated
        if activated:
            import datetime
            data['activation_time'] = datetime.datetime.now().isoformat()
        
        with open(self.efuse_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_identity_info(self) -> dict:
        """Get full identity information."""
        return {
            'mac_address': self.mac_address,
            'serial_number': self.serial_number,
            'client_id': self.client_id,
            'is_activated': self.is_activated()
        }
