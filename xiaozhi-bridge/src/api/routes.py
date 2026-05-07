"""
FastAPI routes for OpenAI-compatible API.
"""

import asyncio
import json
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse

from .schemas import (
    ChatCompletionRequest,
    ChatCompletionChunk,
    ChatCompletionResponse,
    EmotionRequest,
    StatusResponse,
    ActivationStatusResponse,
    ActivationStartResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["api"])


# Global bridge instance (set by main app)
_bridge = None


def set_bridge(bridge):
    """Set the bridge instance."""
    global _bridge
    _bridge = bridge


def get_bridge():
    """Get the bridge instance."""
    if not _bridge:
        raise HTTPException(status_code=503, detail="Bridge not initialized")
    return _bridge


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """Get bridge status."""
    bridge = get_bridge()
    return bridge.get_status()


@router.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-compatible chat completions endpoint.
    
    Streams responses using Server-Sent Events (SSE).
    """
    bridge = get_bridge()
    
    if not bridge.is_connected:
        raise HTTPException(status_code=503, detail="Not connected to Xiaozhi")
    
    # Extract last user message
    user_message = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break
    
    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        """Generate streaming response."""
        try:
            # Send message to Xiaozhi
            await bridge.send_message(user_message)
            
            # Wait and stream response
            chunk_id = 0
            async for chunk in bridge._session.wait_for_response(timeout=120):
                choice = {
                    "index": 0,
                    "delta": {"content": chunk},
                    "finish_reason": None
                }
                
                response = ChatCompletionChunk(
                    choices=[choice]
                )
                
                yield f"data: {response.json()}\n\n"
                chunk_id += 1
            
            # Send final chunk
            final_choice = {
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }
            
            final_response = ChatCompletionChunk(
                choices=[final_choice]
            )
            
            yield f"data: {final_response.json()}\n\n"
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
    
    if request.stream:
        return EventSourceResponse(generate_stream())
    else:
        # Non-streaming mode (collect all chunks first)
        chunks = []
        async for chunk in generate_stream():
            if chunk.startswith("data: ") and not chunk.startswith("data: [DONE]"):
                try:
                    data = json.loads(chunk[6:])
                    if "choices" in data and data["choices"]:
                        content = data["choices"][0].get("delta", {}).get("content", "")
                        if content:
                            chunks.append(content)
                except:
                    pass
        
        response = ChatCompletionResponse(
            choices=[{
                "index": 0,
                "message": {"role": "assistant", "content": "".join(chunks)},
                "finish_reason": "stop"
            }]
        )
        
        return response


@router.post("/emotion")
async def set_emotion(request: EmotionRequest):
    """Set device emotion."""
    bridge = get_bridge()
    
    if not bridge.is_connected:
        raise HTTPException(status_code=503, detail="Not connected to Xiaozhi")
    
    success = await bridge.set_emotion(request.emotion)
    
    if not success:
        raise HTTPException(status_code=400, detail="Invalid emotion")
    
    return {"status": "success", "emotion": request.emotion}


@router.get("/models")
async def list_models():
    """List available models (OpenAI compatibility)."""
    return {
        "object": "list",
        "data": [{
            "id": "xiaozhi-ai",
            "object": "model",
            "created": 1234567890,
            "owned_by": "xiaozhi"
        }]
    }


@router.post("/activate/start", response_model=ActivationStartResponse)
async def start_activation():
    """Start device activation process."""
    bridge = get_bridge()
    
    if bridge.identity.is_activated():
        return ActivationStartResponse(
            success=True,
            user_code="",
            message="Device already activated"
        )
    
    success, user_code = await bridge.activate()
    
    if not success or not user_code:
        raise HTTPException(status_code=500, detail="Failed to start activation")
    
    return ActivationStartResponse(
        success=True,
        user_code=user_code,
        message=f"Enter code {user_code} on xiaozhi.me"
    )


@router.get("/activate/status", response_model=ActivationStatusResponse)
async def activation_status():
    """Check activation status."""
    bridge = get_bridge()
    
    if bridge.identity.is_activated():
        return ActivationStatusResponse(
            activated=True,
            message="Device is activated"
        )
    
    return ActivationStatusResponse(
        activated=False,
        message="Device not activated"
    )


@router.post("/activate/poll")
async def poll_activation():
    """Poll for activation completion."""
    bridge = get_bridge()
    
    if bridge.identity.is_activated():
        return {"status": "already_activated"}
    
    result = await bridge.poll_activation()
    
    if result:
        # Try to connect after successful activation
        connected = await bridge.connect()
        return {
            "status": "activated",
            "connected": connected
        }
    
    return {"status": "pending"}


@router.post("/activate/reset")
async def reset_activation():
    """Reset activation state."""
    bridge = get_bridge()
    bridge.identity.set_activated(False)
    
    # Clear efuse file
    import os
    from pathlib import Path
    efuse_file = Path("/data/efuse.json")
    if efuse_file.exists():
        os.remove(efuse_file)
    
    return {"status": "reset", "message": "Activation state cleared"}
