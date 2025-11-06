"""Supabase database client and helper functions"""
import os
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
from datetime import datetime
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class SupabaseDB:
    """Wrapper for Supabase database operations"""
    
    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        # Use service_role key for backend operations (bypasses RLS)
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment")
        
        self.client: Client = create_client(supabase_url, supabase_key)
    
    # User/Profile operations
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile by ID"""
        try:
            result = self.client.table("profiles").select("*").eq("id", user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting user profile: {e}")
            return None
    
    async def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user profile"""
        try:
            result = self.client.table("profiles").update(updates).eq("id", user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error updating user profile: {e}")
            return None
    
    async def get_profile_by_connection_id(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile by connection_id"""
        try:
            result = self.client.table("profiles").select("*").eq("connection_id", connection_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting profile by connection_id: {e}")
            return None
    
    # Conversation operations
    async def create_conversation(self, user_id: str, title: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Create a new conversation"""
        try:
            result = self.client.table("conversations").insert({
                "user_id": user_id,
                "title": title or "New Conversation"
            }).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating conversation: {e}")
            return None
    
    async def get_user_conversations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all conversations for a user"""
        try:
            result = self.client.table("conversations")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("updated_at", desc=True)\
                .execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error getting user conversations: {e}")
            return []
    
    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific conversation"""
        try:
            result = self.client.table("conversations").select("*").eq("id", conversation_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting conversation: {e}")
            return None
    
    async def get_or_create_active_conversation(self, user_id: str) -> Dict[str, Any]:
        """Get the most recent conversation or create a new one"""
        conversations = await self.get_user_conversations(user_id)
        if conversations:
            return conversations[0]
        return await self.create_conversation(user_id)
    
    # Message operations
    async def create_message(
        self,
        conversation_id: str,
        user_id: str,
        content: str,
        role: str,
        message_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new message"""
        try:
            result = self.client.table("messages").insert({
                "conversation_id": conversation_id,
                "user_id": user_id,
                "content": content,
                "role": role,
                "message_type": message_type,
                "metadata": metadata or {}
            }).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating message: {e}")
            return None
    
    async def get_conversation_messages(
        self,
        conversation_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get messages for a conversation"""
        try:
            result = self.client.table("messages")\
                .select("*")\
                .eq("conversation_id", conversation_id)\
                .order("created_at", desc=False)\
                .limit(limit)\
                .execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error getting conversation messages: {e}")
            return []
    
    async def get_conversation_history_formatted(
        self,
        conversation_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get conversation history formatted for display"""
        messages = await self.get_conversation_messages(conversation_id, limit)
        return [
            {
                "id": msg["id"],
                "type": msg["role"],
                "message": msg["content"],
                "timestamp": msg["created_at"]
            }
            for msg in messages
        ]
    
    # User memory operations
    async def save_user_memory(
        self,
        user_id: str,
        memory_type: str,
        content: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Save user memory/insight"""
        try:
            result = self.client.table("user_memories").insert({
                "user_id": user_id,
                "memory_type": memory_type,
                "content": content
            }).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error saving user memory: {e}")
            return None
    
    async def get_user_memories(
        self,
        user_id: str,
        memory_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user memories, optionally filtered by type"""
        try:
            query = self.client.table("user_memories").select("*").eq("user_id", user_id)
            if memory_type:
                query = query.eq("memory_type", memory_type)
            result = query.order("created_at", desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error getting user memories: {e}")
            return []


# Global database instance
db = SupabaseDB()

