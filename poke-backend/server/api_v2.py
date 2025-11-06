"""Updated API with Supabase authentication and storage"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from typing import Optional
import asyncio

from .database import db
from .auth import auth_service
from .message_processor_v2 import MessageProcessor
from .connection import initiate_connection, get_connection_status
from composio import Composio
from collections import deque
from .notifications import EventNotifier

app = FastAPI(title="Poke AI Backend", version="2.0.0")

# Add CORS middleware
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

raw_origins = os.getenv("CORS_ALLOW_ORIGINS", "")
allowed_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
final_allowed_origins = allowed_origins or DEFAULT_ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=final_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
message_queue = deque()
event_notifier = EventNotifier()
# Database-connected message processor
message_processor = MessageProcessor(message_queue, event_notifier)
composio_client = Composio()


# Request/Response models
class SignUpRequest(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None


class SignInRequest(BaseModel):
    email: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class MessageRequest(BaseModel):
    content: str


class ConnectionRequest(BaseModel):
    auth_config_id: Optional[str] = None


class CoreMemoryUpdateRequest(BaseModel):
    updates: dict


@app.on_event("startup")
async def startup_event():
    """Start the message processor when the API starts"""
    asyncio.create_task(message_processor.start_processing())


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the message processor when the API shuts down"""
    await message_processor.stop_processing()


# Authentication endpoints
@app.post("/auth/signup")
async def sign_up(request: SignUpRequest):
    """Register a new user"""
    return await auth_service.sign_up(
        email=request.email,
        password=request.password,
        full_name=request.full_name
    )


@app.post("/auth/signin")
async def sign_in(request: SignInRequest):
    """Sign in an existing user"""
    return await auth_service.sign_in(
        email=request.email,
        password=request.password
    )


@app.post("/auth/refresh")
async def refresh_session(request: RefreshTokenRequest):
    """Refresh an expired session"""
    return await auth_service.refresh_session(request.refresh_token)


@app.get("/auth/me")
async def get_current_user(user_id: str = Depends(auth_service.verify_token)):
    """Get current authenticated user profile"""
    profile = await db.get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


# User profile endpoints
@app.get("/users/me/profile")
async def get_my_profile(user_id: str = Depends(auth_service.verify_token)):
    """Get current user's profile"""
    profile = await db.get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@app.patch("/users/me/profile")
async def update_my_profile(
    updates: dict,
    user_id: str = Depends(auth_service.verify_token)
):
    """Update current user's profile"""
    profile = await db.update_user_profile(user_id, updates)
    if not profile:
        raise HTTPException(status_code=404, detail="Failed to update profile")
    return profile


# Connection endpoints (Composio Gmail)
@app.post("/connections/initiate")
async def initiate_user_connection(
    request: ConnectionRequest,
    user_id: str = Depends(auth_service.verify_token)
):
    """Initiate Gmail connection for user"""
    try:
        connected_account = initiate_connection(
            user_id=user_id,
            composio_client=composio_client,
            auth_config_id=request.auth_config_id
        )
        
        # Store connection_id in user profile
        await db.update_user_profile(user_id, {"connection_id": connected_account.id})
        
        return {
            "connection_id": connected_account.id,
            "redirect_url": connected_account.redirect_url,
        }
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Connection failed")


@app.get("/connections/status")
async def check_my_connection_status(user_id: str = Depends(auth_service.verify_token)):
    """Check current user's connection status"""
    try:
        profile = await db.get_user_profile(user_id)
        if not profile or not profile.get("connection_id"):
            raise HTTPException(status_code=404, detail="No connection found")
        
        status = get_connection_status(
            connected_account_id=profile["connection_id"],
            composio_client=composio_client
        )
        
        return {"status": status.status, "connection_id": profile["connection_id"]}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Unable to check connection status")


# Conversation endpoints
@app.get("/conversations")
async def get_my_conversations(user_id: str = Depends(auth_service.verify_token)):
    """Get all conversations for current user"""
    conversations = await db.get_user_conversations(user_id)
    return {"conversations": conversations}


@app.post("/conversations")
async def create_conversation(
    title: Optional[str] = None,
    user_id: str = Depends(auth_service.verify_token)
):
    """Create a new conversation"""
    conversation = await db.create_conversation(user_id, title)
    if not conversation:
        raise HTTPException(status_code=500, detail="Failed to create conversation")
    return conversation


@app.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user_id: str = Depends(auth_service.verify_token)
):
    """Get a specific conversation with messages"""
    conversation = await db.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Verify ownership
    if conversation["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    messages = await db.get_conversation_messages(conversation_id)
    return {
        "conversation": conversation,
        "messages": messages
    }


# Message endpoints
@app.post("/messages")
async def send_message(
    request: MessageRequest,
    user_id: str = Depends(auth_service.verify_token)
):
    """Send a message to the agent"""
    try:
        # Get or create active conversation
        conversation = await db.get_or_create_active_conversation(user_id)
        
        # Save user message
        user_message = await db.create_message(
            conversation_id=conversation["id"],
            user_id=user_id,
            content=request.content,
            role="user"
        )
        
        if not user_message:
            raise HTTPException(status_code=500, detail="Failed to save message")
        
        # Queue the message for processing
        message_id = await message_processor.queue_user_message(user_id, request.content)
        
        if message_id:
            return {
                "message_id": message_id,
                "conversation_id": conversation["id"],
                "status": "queued"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to queue message")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Message processing failed")


@app.get("/messages/{message_id}/response")
async def get_message_response(
    message_id: str,
    user_id: str = Depends(auth_service.verify_token)
):
    """Get response for a specific message"""
    try:
        response_data = message_processor.get_message_response(message_id)
        if response_data.get("status") == "not_found":
            raise HTTPException(status_code=404, detail="Message not found")
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get message response")


# User memory endpoints
@app.get("/memories")
async def get_my_memories(user_id: str = Depends(auth_service.verify_token)):
    """Get user memories and insights"""
    memories = await db.get_user_memories(user_id)
    return {"memories": memories}


# WebSocket endpoint
@app.websocket("/ws/users/me")
async def user_updates(
    websocket: WebSocket,
    token: Optional[str] = None
):
    """WebSocket connection for real-time updates (requires token in query param)"""
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return
    
    try:
        # Verify token
        user_id = await auth_service.verify_token(f"Bearer {token}")
    except HTTPException:
        await websocket.close(code=1008, reason="Invalid token")
        return
    
    await event_notifier.connect(user_id, websocket)
    
    try:
        # Send conversation history
        conversation = await db.get_or_create_active_conversation(user_id)
        messages = await db.get_conversation_history_formatted(conversation["id"])
        
        await websocket.send_json({
            "type": "conversation_snapshot",
            "conversations": messages,
        })
        
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        event_notifier.disconnect(user_id, websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        event_notifier.disconnect(user_id, websocket)


# Memory Management endpoints
@app.get("/memory/core")
async def get_core_memory(user_id: str = Depends(auth_service.verify_token)):
    """Get user's core memory"""
    try:
        from .memory import memory_manager
        core_memory = await memory_manager.get_core_memory(user_id)
        return {
            "success": True,
            "core_memory": core_memory.to_dict(),
            "prompt_preview": core_memory.to_prompt_string()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve core memory: {str(e)}")


@app.post("/memory/core")
async def update_core_memory(
    request: CoreMemoryUpdateRequest,
    user_id: str = Depends(auth_service.verify_token)
):
    """Update user's core memory"""
    try:
        from .memory import memory_manager
        updated_memory = await memory_manager.update_core_memory(
            user_id=user_id,
            updates=request.updates,
            merge=True
        )
        return {
            "success": True,
            "core_memory": updated_memory.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update core memory: {str(e)}")


@app.post("/memory/extract")
async def extract_memory_from_text(
    request: MessageRequest,
    user_id: str = Depends(auth_service.verify_token)
):
    """Manually trigger memory extraction from a piece of text (for testing)"""
    try:
        from .memory import memory_manager
        updated_memory = await memory_manager.extract_and_update_memory(
            user_id=user_id,
            conversation_text=request.content
        )
        return {
            "success": True,
            "core_memory": updated_memory.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract memory: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

