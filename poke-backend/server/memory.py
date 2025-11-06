"""Core Memory Management System for Carl Healthcare Agent

This module implements a three-tier memory architecture:
- Tier 1: Working Memory (conversation history - handled by message system)
- Tier 2: Core Memory (structured user facts - always loaded)
- Tier 3: Long-term Memory (episodic/semantic - retrieval-based, future phase)
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
import json
import logging

from .database import db

logger = logging.getLogger(__name__)


class CoreMemorySchema(BaseModel):
    """Structured schema for core user facts that are always available to the agent"""
    
    # Identity
    user_name: Optional[str] = Field(None, description="User's preferred name")
    care_role: Optional[str] = Field(None, description="'self' or 'caregiver'")
    care_recipient_name: Optional[str] = Field(None, description="Name of person being cared for (if caregiver)")
    
    # Location & Contact
    zip_code: Optional[str] = Field(None, description="ZIP code for local resources")
    preferred_contact_time: Optional[str] = Field(None, description="Preferred time window for contact")
    communication_preferences: Optional[str] = Field(None, description="How user prefers to communicate")
    
    # Insurance
    insurance_carrier: Optional[str] = Field(None, description="Insurance company name")
    plan_type: Optional[str] = Field(None, description="Type of insurance plan (e.g., Medicare, Medicaid, PPO)")
    plan_nickname: Optional[str] = Field(None, description="User's nickname for their plan")
    
    # Health Information
    medications: List[str] = Field(default_factory=list, description="Current medications")
    upcoming_appointments: List[Dict[str, Any]] = Field(default_factory=list, description="Scheduled appointments")
    
    # Preferences & Notes
    key_concerns: List[str] = Field(default_factory=list, description="Main health/care concerns")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences and settings")
    
    # Metadata
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values"""
        return {k: v for k, v in self.model_dump().items() if v is not None and v != [] and v != {}}
    
    def to_prompt_string(self) -> str:
        """Format core memory for injection into agent prompts"""
        lines = ["=== USER CORE MEMORY ==="]
        
        if self.user_name:
            lines.append(f"Name: {self.user_name}")
        
        if self.care_role:
            role_text = f"Role: Helping {self.care_role}"
            if self.care_role == "caregiver" and self.care_recipient_name:
                role_text += f" (caring for {self.care_recipient_name})"
            lines.append(role_text)
        
        if self.zip_code:
            lines.append(f"Location: ZIP {self.zip_code}")
        
        if self.insurance_carrier or self.plan_type:
            insurance_parts = []
            if self.insurance_carrier:
                insurance_parts.append(self.insurance_carrier)
            if self.plan_type:
                insurance_parts.append(f"({self.plan_type})")
            lines.append(f"Insurance: {' '.join(insurance_parts)}")
        
        if self.medications:
            lines.append(f"Medications: {', '.join(self.medications)}")
        
        if self.upcoming_appointments:
            appt_strs = [f"{a.get('type', 'appointment')} on {a.get('date', 'TBD')}" 
                        for a in self.upcoming_appointments[:3]]  # Show max 3
            lines.append(f"Upcoming: {', '.join(appt_strs)}")
        
        if self.key_concerns:
            lines.append(f"Key concerns: {', '.join(self.key_concerns)}")
        
        if self.preferred_contact_time:
            lines.append(f"Preferred contact: {self.preferred_contact_time}")
        
        lines.append("=== END CORE MEMORY ===")
        return "\n".join(lines)


class MemoryManager:
    """Manages core memory operations for users"""
    
    CORE_MEMORY_TYPE = "core_memory"
    
    async def get_core_memory(self, user_id: str) -> CoreMemorySchema:
        """Retrieve user's core memory, or create empty if doesn't exist"""
        try:
            memories = await db.get_user_memories(user_id, memory_type=self.CORE_MEMORY_TYPE)
            
            if memories and len(memories) > 0:
                # Get the most recent core memory
                latest = memories[0]
                return CoreMemorySchema(**latest["content"])
            
            # Return empty core memory
            return CoreMemorySchema()
            
        except Exception as e:
            logger.error(f"Error retrieving core memory for user {user_id}: {e}")
            return CoreMemorySchema()
    
    async def update_core_memory(
        self, 
        user_id: str, 
        updates: Dict[str, Any],
        merge: bool = True
    ) -> CoreMemorySchema:
        """
        Update user's core memory
        
        Args:
            user_id: User ID
            updates: Dictionary of fields to update
            merge: If True, merge with existing memory. If False, replace entirely.
        
        Returns:
            Updated CoreMemorySchema
        """
        try:
            if merge:
                # Get existing memory and merge
                current = await self.get_core_memory(user_id)
                current_dict = current.to_dict()
                
                # Merge updates
                for key, value in updates.items():
                    if key in CoreMemorySchema.model_fields:
                        current_dict[key] = value
                
                updated = CoreMemorySchema(**current_dict)
            else:
                # Replace entirely
                updated = CoreMemorySchema(**updates)
            
            updated.last_updated = datetime.utcnow().isoformat()
            
            # Save to database
            await db.save_user_memory(
                user_id=user_id,
                memory_type=self.CORE_MEMORY_TYPE,
                content=updated.to_dict()
            )
            
            logger.info(f"Updated core memory for user {user_id}")
            return updated
            
        except Exception as e:
            logger.error(f"Error updating core memory for user {user_id}: {e}")
            return await self.get_core_memory(user_id)  # Return existing on error
    
    async def extract_and_update_memory(
        self,
        user_id: str,
        conversation_text: str,
        agent_response: Optional[str] = None
    ) -> CoreMemorySchema:
        """
        Extract facts from conversation and update core memory
        
        This uses the LLM to identify extractable facts from the conversation
        and automatically updates the core memory.
        
        Args:
            user_id: User ID
            conversation_text: Recent conversation context
            agent_response: Agent's response (optional, for context)
        
        Returns:
            Updated CoreMemorySchema
        """
        try:
            print(f"[MEMORY EXTRACT] Loading OpenAI model...")
            from .constants import openai
            from langchain_core.messages import SystemMessage, HumanMessage
            
            print(f"[MEMORY EXTRACT] Getting current memory for user {user_id}")
            current_memory = await self.get_core_memory(user_id)
            
            extraction_prompt = f"""You are a memory extraction assistant. Extract factual information about the user from their message.

Current Memory: {json.dumps(current_memory.to_dict(), indent=2) if current_memory.to_dict() else "Empty"}

User's Message: "{conversation_text}"
{f'Agent Response: "{agent_response}"' if agent_response else ''}

Extract ONLY facts explicitly stated by the user. Return a JSON object with these fields (omit fields with no information):

- user_name: The user's first name
- care_role: "self" (if helping themselves) or "caregiver" (if helping someone else)
- care_recipient_name: Name/relation of person being cared for (e.g., "mom", "dad", "John")
- zip_code: ZIP code as a string
- insurance_carrier: Insurance company name
- plan_type: Type of insurance plan
- medications: List of medication names
- key_concerns: List of health concerns mentioned

Examples:

User: "My name is Sarah and I live in 90210"
Output: {{"user_name": "Sarah", "zip_code": "90210"}}

User: "I'm helping my mom who has UnitedHealthcare Medicare"
Output: {{"care_role": "caregiver", "care_recipient_name": "mom", "insurance_carrier": "UnitedHealthcare", "plan_type": "Medicare"}}

User: "I take Metformin for my diabetes"
Output: {{"medications": ["Metformin"], "key_concerns": ["diabetes"]}}

Now extract from the user's message above. Return ONLY the JSON object, no explanation:"""

            print(f"[MEMORY EXTRACT] Calling LLM for extraction...")
            response = await openai.ainvoke([
                SystemMessage(content="You extract facts from user messages. Return valid JSON only, no markdown, no explanations."),
                HumanMessage(content=extraction_prompt)
            ])
            
            print(f"[MEMORY EXTRACT] LLM response received, parsing...")
            # Parse the response
            response_text = response.content.strip()
            print(f"[MEMORY EXTRACT] Raw response: {response_text[:200]}...")
            
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            extracted_facts = json.loads(response_text)
            print(f"[MEMORY EXTRACT] Parsed facts: {extracted_facts}")
            
            if extracted_facts:
                print(f"[MEMORY EXTRACT] Updating memory with new facts...")
                logger.info(f"Extracted facts for user {user_id}: {extracted_facts}")
                return await self.update_core_memory(user_id, extracted_facts, merge=True)
            else:
                print(f"[MEMORY EXTRACT] No new facts to extract")
                logger.debug(f"No new facts extracted for user {user_id}")
                return current_memory
                
        except Exception as e:
            logger.error(f"Error extracting memory for user {user_id}: {e}")
            logger.debug(f"Full error: {type(e).__name__}: {str(e)}")
            return await self.get_core_memory(user_id)


# Global memory manager instance
memory_manager = MemoryManager()

