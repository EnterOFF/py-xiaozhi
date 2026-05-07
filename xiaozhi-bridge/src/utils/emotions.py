"""
Emotion handling utilities.
Manages emotion states and translations between systems.
"""

from enum import Enum
from typing import Optional, Set
import logging

logger = logging.getLogger(__name__)


class Emotion(Enum):
    """Supported emotions for the bridge."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    
    @classmethod
    def from_string(cls, value: str) -> Optional['Emotion']:
        """Convert string to Emotion enum."""
        try:
            return cls(value.lower())
        except ValueError:
            logger.warning(f"Unknown emotion: {value}")
            return None
    
    @classmethod
    def get_all_values(cls) -> Set[str]:
        """Get all valid emotion values."""
        return {e.value for e in cls}


class EmotionManager:
    """Manages emotion state for the bridge."""
    
    def __init__(self):
        self._current_emotion: Emotion = Emotion.NEUTRAL
        self._emotion_history: list[dict] = []
    
    @property
    def current_emotion(self) -> Emotion:
        """Get current emotion."""
        return self._current_emotion
    
    def set_emotion(self, emotion: str | Emotion) -> bool:
        """
        Set current emotion.
        
        Args:
            emotion: Either Emotion enum or string value
            
        Returns:
            True if emotion was changed, False if invalid
        """
        if isinstance(emotion, Emotion):
            new_emotion = emotion
        else:
            new_emotion = Emotion.from_string(emotion)
            if not new_emotion:
                return False
        
        if new_emotion != self._current_emotion:
            old_emotion = self._current_emotion
            self._current_emotion = new_emotion
            
            # Record history
            self._emotion_history.append({
                'from': old_emotion.value,
                'to': new_emotion.value,
            })
            
            # Keep history limited
            if len(self._emotion_history) > 100:
                self._emotion_history = self._emotion_history[-100:]
            
            logger.info(f"Emotion changed: {old_emotion.value} → {new_emotion.value}")
            return True
        
        return False
    
    def get_emotion_state(self) -> dict:
        """Get current emotion state as dictionary."""
        return {
            'emotion': self._current_emotion.value,
            'history_count': len(self._emotion_history)
        }
    
    def translate_to_xiaozhi(self, emotion: str) -> Optional[dict]:
        """
        Translate emotion to Xiaozhi protocol format.
        
        Args:
            emotion: Emotion string
            
        Returns:
            Dict suitable for Xiaozhi WebSocket/MQTT message
        """
        emo = Emotion.from_string(emotion)
        if not emo:
            return None
        
        # Xiaozhi expects JSON with emotion field
        return {
            "type": "llm",
            "emotion": emo.value
        }
    
    def translate_from_xiaozhi(self, data: dict) -> Optional[str]:
        """
        Translate emotion from Xiaozhi protocol format.
        
        Args:
            data: Message dict from Xiaozhi
            
        Returns:
            Emotion string or None
        """
        if data.get('type') != 'llm':
            return None
        
        emotion = data.get('emotion')
        if not emotion:
            return None
        
        emo = Emotion.from_string(emotion)
        return emo.value if emo else None
