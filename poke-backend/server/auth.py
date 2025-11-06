"""Authentication utilities for Supabase"""
import os
from typing import Optional
from fastapi import HTTPException, Header
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class AuthService:
    """Handle Supabase authentication"""
    
    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        self.client: Client = create_client(supabase_url, supabase_key)
    
    async def verify_token(self, authorization: Optional[str] = Header(None)) -> str:
        """Verify JWT token and return user ID"""
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header format")
        
        token = authorization.replace("Bearer ", "")
        
        try:
            # Verify the JWT token with Supabase
            user = self.client.auth.get_user(token)
            if not user or not user.user:
                raise HTTPException(status_code=401, detail="Invalid token")
            return user.user.id
        except Exception as e:
            print(f"Token verification error: {e}")
            raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    async def sign_up(self, email: str, password: str, full_name: Optional[str] = None) -> dict:
        """Sign up a new user"""
        try:
            metadata = {}
            if full_name:
                metadata["full_name"] = full_name
            
            response = self.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {"data": metadata}
            })
            
            if not response.user:
                raise HTTPException(status_code=400, detail="Failed to create user")
            
            return {
                "user": {
                    "id": response.user.id,
                    "email": response.user.email,
                    "full_name": full_name
                },
                "session": {
                    "access_token": response.session.access_token if response.session else None,
                    "refresh_token": response.session.refresh_token if response.session else None
                }
            }
        except Exception as e:
            print(f"Sign up error: {e}")
            raise HTTPException(status_code=400, detail=str(e))
    
    async def sign_in(self, email: str, password: str) -> dict:
        """Sign in an existing user"""
        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if not response.user or not response.session:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            return {
                "user": {
                    "id": response.user.id,
                    "email": response.user.email
                },
                "session": {
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token
                }
            }
        except Exception as e:
            print(f"Sign in error: {e}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
    
    async def refresh_session(self, refresh_token: str) -> dict:
        """Refresh an expired session"""
        try:
            response = self.client.auth.refresh_session(refresh_token)
            
            if not response.session:
                raise HTTPException(status_code=401, detail="Failed to refresh session")
            
            return {
                "session": {
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token
                }
            }
        except Exception as e:
            print(f"Refresh session error: {e}")
            raise HTTPException(status_code=401, detail="Failed to refresh session")


# Global auth service instance
auth_service = AuthService()

