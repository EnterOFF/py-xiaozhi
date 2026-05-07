"""
Pydantic schemas for API requests/responses.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ChatMessage(BaseModel):
    """Single chat message."""
    role: str = Field(..., description="Message role (user/assistant/system)")
    content: str = Field(..., description="Message content")


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""
    model: str = Field(default="xiaozhi-ai", description="Model name")
    messages: List[ChatMessage] = Field(..., description="Chat messages")
    stream: bool = Field(default=True, description="Enable streaming response")
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, gt=0)
    

class ChatCompletionChunk(BaseModel):
    """Streaming response chunk."""
    id: str = "chatcmpl-bridge"
    object: str = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    model: str = "xiaozhi-ai"
    choices: List[Dict[str, Any]]
    

class ChatCompletionResponse(BaseModel):
    """Complete chat completion response."""
    id: str = "chatcmpl-bridge"
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    model: str = "xiaozhi-ai"
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, int]] = None


class EmotionRequest(BaseModel):
    """Emotion setting request."""
    emotion: str = Field(..., description="Emotion name")


class StatusResponse(BaseModel):
    """Bridge status response."""
    activated: bool
    connected: bool
    mac_address: str
    serial_number: str
    protocol: str
    emotion: str


class ActivationStatusResponse(BaseModel):
    """Activation status response."""
    activated: bool
    user_code: Optional[str] = None
    message: str


class ActivationStartResponse(BaseModel):
    """Response when starting activation."""
    success: bool
    user_code: str
    message: str
