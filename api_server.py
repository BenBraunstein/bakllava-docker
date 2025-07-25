#!/usr/bin/env python3

import asyncio
import base64
import io
import json
import logging
import os
import time
import uuid
from typing import List, Optional, Union, Dict
from pathlib import Path
from datetime import datetime, timedelta

import httpx
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app initialization
app = FastAPI(
    title="Bakllava 7B API Server",
    description="API server for Bakllava 7B vision-language model with support for text, images, video frames, and conversation history",
    version="1.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "bakllava"

# In-memory conversation storage (in production, use Redis or database)
conversations: Dict[str, Dict] = {}
CONVERSATION_TIMEOUT = timedelta(hours=24)  # Conversations expire after 24 hours

class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    images: Optional[List[str]] = None  # Base64 encoded images

class ConversationSession(BaseModel):
    session_id: str
    messages: List[Message]
    created_at: datetime
    last_activity: datetime

class TextPromptRequest(BaseModel):
    prompt: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    session_id: Optional[str] = None  # For conversation continuity

class ImagePromptRequest(BaseModel):
    prompt: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    session_id: Optional[str] = None

class VideoFramesRequest(BaseModel):
    prompt: str
    frame_rate: Optional[float] = 1.0
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    session_id: Optional[str] = None

class APIResponse(BaseModel):
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None
    session_id: Optional[str] = None

class ConversationResponse(BaseModel):
    session_id: str
    messages: List[Message]
    total_messages: int

def cleanup_expired_conversations():
    """Remove expired conversations from memory."""
    current_time = datetime.now()
    expired_sessions = []
    
    for session_id, conversation in conversations.items():
        if current_time - conversation["last_activity"] > CONVERSATION_TIMEOUT:
            expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        del conversations[session_id]
        logger.info(f"Expired conversation session: {session_id}")

def get_or_create_conversation(session_id: Optional[str] = None) -> str:
    """Get existing conversation or create a new one."""
    cleanup_expired_conversations()
    
    if session_id and session_id in conversations:
        # Update last activity
        conversations[session_id]["last_activity"] = datetime.now()
        return session_id
    
    # Create new conversation
    new_session_id = str(uuid.uuid4())
    conversations[new_session_id] = {
        "session_id": new_session_id,
        "messages": [],
        "created_at": datetime.now(),
        "last_activity": datetime.now()
    }
    
    logger.info(f"Created new conversation session: {new_session_id}")
    return new_session_id

def add_message_to_conversation(session_id: str, role: str, content: str, images: Optional[List[str]] = None):
    """Add a message to the conversation history."""
    if session_id not in conversations:
        return
    
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now(),
        "images": images
    }
    
    conversations[session_id]["messages"].append(message)
    conversations[session_id]["last_activity"] = datetime.now()

def build_conversation_context(session_id: str, current_prompt: str, current_images: Optional[List[str]] = None) -> tuple[str, Optional[List[str]]]:
    """Build the full conversation context for the model."""
    if session_id not in conversations:
        return current_prompt, current_images
    
    conversation = conversations[session_id]
    messages = conversation["messages"]
    
    if not messages:
        return current_prompt, current_images
    
    # Build conversation context
    context_parts = ["This is a conversation. Here's the conversation history:"]
    
    # Add recent message history (limit to last 10 messages to avoid token limits)
    recent_messages = messages[-10:] if len(messages) > 10 else messages
    
    for msg in recent_messages:
        role = "Human" if msg["role"] == "user" else "Assistant"
        if msg.get("images"):
            context_parts.append(f"{role}: {msg['content']} [with image(s)]")
        else:
            context_parts.append(f"{role}: {msg['content']}")
    
    # Add current prompt
    context_parts.append(f"Human: {current_prompt}")
    context_parts.append("Assistant:")
    
    full_context = "\n\n".join(context_parts)
    
    # For images, only use the current images (conversation image history is complex)
    return full_context, current_images

def image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 string."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()
    return base64.b64encode(image_bytes).decode()

def process_uploaded_file(file: UploadFile) -> Image.Image:
    """Process uploaded file and return PIL Image."""
    try:
        image = Image.open(file.file)
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        return image
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")

async def check_ollama_health():
    """Check if Ollama service is running."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            return response.status_code == 200
    except Exception:
        return False

async def ensure_model_available():
    """Ensure Bakllava model is available in Ollama."""
    try:
        async with httpx.AsyncClient() as client:
            # Check if model is already available
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                for model in models:
                    if MODEL_NAME in model.get("name", ""):
                        logger.info(f"Model {MODEL_NAME} is already available")
                        return True
            
            # Pull the model if not available
            logger.info(f"Pulling model {MODEL_NAME}...")
            pull_response = await client.post(
                f"{OLLAMA_BASE_URL}/api/pull",
                json={"name": MODEL_NAME},
                timeout=300.0
            )
            
            if pull_response.status_code == 200:
                logger.info(f"Model {MODEL_NAME} pulled successfully")
                return True
            else:
                logger.error(f"Failed to pull model: {pull_response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error ensuring model availability: {str(e)}")
        return False

async def generate_response(prompt: str, images: Optional[List[str]] = None, temperature: float = 0.7, max_tokens: int = 2048) -> str:
    """Generate response from Ollama."""
    try:
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        if images:
            payload["images"] = images
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "No response generated")
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ollama API error: {response.text}"
                )
                
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation error: {str(e)}")

@app.on_event("startup")
async def startup_event():
    """Startup event to check Ollama health and model availability."""
    logger.info("Starting Bakllava API server...")
    
    # Wait for Ollama to be ready
    max_retries = 30
    for i in range(max_retries):
        if await check_ollama_health():
            logger.info("Ollama service is ready")
            break
        if i == max_retries - 1:
            logger.error("Ollama service is not responding after 30 attempts")
            raise Exception("Ollama service unavailable")
        logger.info(f"Waiting for Ollama service... ({i+1}/{max_retries})")
        await asyncio.sleep(2)
    
    # Ensure model is available
    if not await ensure_model_available():
        logger.warning("Model may not be available, but continuing...")

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Bakllava 7B API Server",
        "version": "1.1.0",
        "features": ["text", "images", "video", "conversations"],
        "endpoints": {
            "text": "/api/text",
            "image": "/api/image", 
            "video": "/api/video",
            "conversation": "/api/conversation/{session_id}",
            "new_conversation": "/api/conversation/new",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    ollama_healthy = await check_ollama_health()
    return {
        "status": "healthy" if ollama_healthy else "unhealthy",
        "ollama": ollama_healthy,
        "model": MODEL_NAME,
        "active_conversations": len(conversations)
    }

@app.post("/api/conversation/new")
async def create_new_conversation():
    """Create a new conversation session."""
    session_id = get_or_create_conversation()
    return {
        "session_id": session_id,
        "message": "New conversation created"
    }

@app.get("/api/conversation/{session_id}")
async def get_conversation(session_id: str):
    """Get conversation history."""
    if session_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversation = conversations[session_id]
    return ConversationResponse(
        session_id=session_id,
        messages=[Message(**msg) for msg in conversation["messages"]],
        total_messages=len(conversation["messages"])
    )

@app.delete("/api/conversation/{session_id}")
async def delete_conversation(session_id: str):
    """Delete a conversation."""
    if session_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    del conversations[session_id]
    return {"message": f"Conversation {session_id} deleted"}

@app.post("/api/text", response_model=APIResponse)
async def text_prompt(request: TextPromptRequest):
    """Handle text-only prompts with optional conversation context."""
    start_time = time.time()
    
    try:
        # Get or create conversation
        session_id = get_or_create_conversation(request.session_id)
        
        # Build conversation context
        context_prompt, _ = build_conversation_context(session_id, request.prompt)
        
        # Add user message to conversation
        add_message_to_conversation(session_id, "user", request.prompt)
        
        response = await generate_response(
            prompt=context_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        # Add assistant response to conversation
        add_message_to_conversation(session_id, "assistant", response)
        
        processing_time = time.time() - start_time
        
        return APIResponse(
            success=True,
            response=response,
            processing_time=processing_time,
            session_id=session_id
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Text prompt error: {str(e)}")
        return APIResponse(
            success=False,
            error=str(e),
            processing_time=processing_time,
            session_id=request.session_id
        )

@app.post("/api/image", response_model=APIResponse)
async def image_prompt(
    prompt: str = Form(...),
    temperature: float = Form(0.7),
    max_tokens: int = Form(2048),
    session_id: Optional[str] = Form(None),
    image: UploadFile = File(...)
):
    """Handle prompts with a single image and optional conversation context."""
    start_time = time.time()
    
    try:
        # Get or create conversation
        session_id = get_or_create_conversation(session_id)
        
        # Process the uploaded image
        pil_image = process_uploaded_file(image)
        image_b64 = image_to_base64(pil_image)
        
        # Build conversation context
        context_prompt, context_images = build_conversation_context(session_id, prompt, [image_b64])
        
        # Add user message to conversation (with image)
        add_message_to_conversation(session_id, "user", prompt, [image_b64])
        
        response = await generate_response(
            prompt=context_prompt,
            images=context_images,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Add assistant response to conversation
        add_message_to_conversation(session_id, "assistant", response)
        
        processing_time = time.time() - start_time
        
        return APIResponse(
            success=True,
            response=response,
            processing_time=processing_time,
            session_id=session_id
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Image prompt error: {str(e)}")
        return APIResponse(
            success=False,
            error=str(e),
            processing_time=processing_time,
            session_id=session_id
        )

@app.post("/api/video", response_model=APIResponse)
async def video_frames_prompt(
    prompt: str = Form(...),
    frame_rate: float = Form(1.0),
    temperature: float = Form(0.7),
    max_tokens: int = Form(2048),
    session_id: Optional[str] = Form(None),
    frames: List[UploadFile] = File(...)
):
    """Handle prompts with multiple images as video frames and optional conversation context."""
    start_time = time.time()
    
    try:
        if not frames:
            raise HTTPException(status_code=400, detail="No frames provided")
        
        if len(frames) > 30:  # Limit to 30 frames to prevent memory issues
            raise HTTPException(status_code=400, detail="Too many frames (max 30)")
        
        # Get or create conversation
        session_id = get_or_create_conversation(session_id)
        
        # Process all frames
        image_b64_list = []
        for i, frame in enumerate(frames):
            try:
                pil_image = process_uploaded_file(frame)
                image_b64 = image_to_base64(pil_image)
                image_b64_list.append(image_b64)
            except Exception as e:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Error processing frame {i+1}: {str(e)}"
                )
        
        # Add frame context to prompt
        enhanced_prompt = f"{prompt}\n\nThis is a sequence of {len(frames)} video frames captured at {frame_rate} frame(s) per second."
        
        # Build conversation context
        context_prompt, context_images = build_conversation_context(session_id, enhanced_prompt, image_b64_list)
        
        # Add user message to conversation (with video frames)
        add_message_to_conversation(session_id, "user", enhanced_prompt, image_b64_list)
        
        response = await generate_response(
            prompt=context_prompt,
            images=context_images,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Add assistant response to conversation
        add_message_to_conversation(session_id, "assistant", response)
        
        processing_time = time.time() - start_time
        
        return APIResponse(
            success=True,
            response=response,
            processing_time=processing_time,
            session_id=session_id
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Video frames prompt error: {str(e)}")
        return APIResponse(
            success=False,
            error=str(e),
            processing_time=processing_time,
            session_id=session_id
        )

if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    ) 