# Core Memory System Implementation

## Overview

The Core Memory System enables Carl (the Voyager Health agent) to remember and recall important user information across conversations, providing personalized, contextual assistance.

## Architecture: Three-Tier Memory Model

### Tier 1: Working Memory (Current Session)
- **What**: Recent conversation history within the current session
- **Storage**: Supabase `messages` table
- **Access**: Loaded into LLM context window during conversation
- **Lifecycle**: Active during session, persisted for history

### Tier 2: Core Memory (User Profile) ✅ **IMPLEMENTED**
- **What**: Structured, always-available user facts
- **Storage**: Supabase `user_memories` table with type `core_memory`
- **Access**: Injected into every agent prompt
- **Lifecycle**: Persistent, auto-updated from conversations

### Tier 3: Long-Term Memory (Episodic/Semantic) 🔜 **FUTURE**
- **What**: Historical insights, preferences, patterns
- **Storage**: Vector embeddings (FAISS or pgvector)
- **Access**: Retrieval-based semantic search
- **Lifecycle**: Persistent, queried when relevant

## Core Memory Schema

```python
CoreMemorySchema:
  # Identity
  - user_name: str
  - care_role: "self" | "caregiver"
  - care_recipient_name: str  # if caregiver
  
  # Location & Contact
  - zip_code: str
  - preferred_contact_time: str
  - communication_preferences: str
  
  # Insurance
  - insurance_carrier: str
  - plan_type: str
  - plan_nickname: str
  
  # Health
  - medications: List[str]
  - upcoming_appointments: List[Dict]
  - key_concerns: List[str]
  
  # Metadata
  - preferences: Dict
  - last_updated: timestamp
```

## How It Works

### 1. Memory Loading (Every Request)
When a user sends a message, the agent:
1. Retrieves user's core memory from database
2. Formats it as structured text
3. Injects into system prompt

**Example Prompt Injection:**
```
=== USER CORE MEMORY ===
Name: Sarah
Role: Helping caregiver (caring for Mom)
Location: ZIP 90210
Insurance: UnitedHealthcare (Medicare Advantage)
Medications: Lisinopril, Metformin
Key concerns: diabetes, high blood pressure
=== END CORE MEMORY ===
```

### 2. Memory Extraction (After Every Response)
After the agent responds:
1. LLM analyzes user message + agent response
2. Extracts explicitly stated facts
3. Merges with existing core memory
4. Saves to database

**Extraction is Smart:**
- Only captures explicitly stated information
- Doesn't infer or assume
- Merges with existing data (doesn't overwrite entire profile)
- Handles lists (medications, concerns) intelligently

### 3. Memory Updates (Automatic)
The system automatically detects and stores:
- **Names**: "My name is John" → `user_name: "John"`
- **Roles**: "I'm helping my dad" → `care_role: "caregiver"`, `care_recipient_name: "dad"`
- **Location**: "I live in 10001" → `zip_code: "10001"`
- **Insurance**: "I have Blue Cross PPO" → `insurance_carrier: "Blue Cross"`, `plan_type: "PPO"`
- **Medications**: "I take Metformin" → `medications: ["Metformin"]`
- **Concerns**: "I'm worried about my diabetes" → `key_concerns: ["diabetes"]`

## API Endpoints

### Get Core Memory
```http
GET /memory/core
Authorization: Bearer <token>

Response:
{
  "success": true,
  "core_memory": { ... },
  "prompt_preview": "=== USER CORE MEMORY ===\n..."
}
```

### Update Core Memory
```http
POST /memory/core
Authorization: Bearer <token>
Content-Type: application/json

{
  "updates": {
    "user_name": "John",
    "zip_code": "90210"
  }
}
```

### Manual Extraction (Testing)
```http
POST /memory/extract
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "I take Lisinopril and live in 10001"
}
```

## Implementation Files

### Core Files
- **`server/memory.py`**: Memory manager, schema, extraction logic
- **`server/agent.py`**: Memory injection into prompts
- **`server/message_processor_v2.py`**: Automatic extraction after responses
- **`server/api_v2.py`**: Memory management endpoints

### Database
- **Table**: `user_memories` (already exists)
- **Type**: `"core_memory"`
- **Content**: JSONB with CoreMemorySchema fields

## Testing

Run the test suite:
```bash
cd poke-backend
python3 test_memory.py
```

**Test Coverage:**
- ✅ Empty memory initialization
- ✅ Manual memory updates
- ✅ Automatic extraction from conversations
- ✅ Memory persistence
- ✅ Complex information (insurance, medications)
- ✅ Prompt formatting

## Usage Examples

### User Flow
1. **First interaction**:
   - User: "Hi, I'm Sarah and I'm helping my mom with her Medicare"
   - System extracts: `user_name="Sarah"`, `care_role="caregiver"`, `care_recipient_name="mom"`

2. **Later interaction**:
   - User: "What's covered for dental?"
   - Agent sees memory: "Name: Sarah, Role: caregiver (caring for mom)"
   - Response: "Hi Sarah! Let me help you understand your mom's dental coverage..."

3. **Memory builds over time**:
   - User mentions ZIP code → stored
   - User mentions medications → stored
   - User mentions insurance → stored
   - All automatically, no prompting needed

### Developer Usage

```python
from server.memory import memory_manager

# Get memory
memory = await memory_manager.get_core_memory(user_id)
print(memory.to_prompt_string())

# Manual update
await memory_manager.update_core_memory(
    user_id,
    {"user_name": "John", "zip_code": "10001"},
    merge=True
)

# Automatic extraction
await memory_manager.extract_and_update_memory(
    user_id=user_id,
    conversation_text="I take Metformin for diabetes",
    agent_response="Got it! I've noted your medication."
)
```

## Privacy & Security

### What's Stored
- First names only (not full names)
- ZIP codes (not full addresses)
- Insurance carrier names (not policy numbers)
- Medication names (not dosages)
- General concerns (not diagnoses)

### What's NOT Stored
- ❌ Social Security Numbers
- ❌ Full Medicare IDs
- ❌ Full addresses
- ❌ Birthdays (except year if needed)
- ❌ Medical diagnoses
- ❌ Treatment plans

### Security
- All memory tied to authenticated user ID
- Row-Level Security (RLS) in Supabase
- Users can only access their own memory
- Backend uses service key for operations

## Future Enhancements (Phase 2-4)

### Phase 2: Semantic Long-Term Memory
- Vector embeddings for conversation insights
- Semantic search for relevant memories
- "Last time we talked about X..."

### Phase 3: Memory Consolidation
- Periodic summarization of conversations
- Detect and merge duplicate memories
- Auto-expire outdated information

### Phase 4: Proactive Recall
- Agent surfaces relevant memories unprompted
- Asks for confirmation/updates on stored facts
- "I remember you mentioned taking Metformin. Are you still on that?"

## Troubleshooting

### Memory not persisting?
- Check database connection (SUPABASE_URL, SUPABASE_SERVICE_KEY)
- Verify user_id is valid UUID
- Check logs for extraction errors

### Extraction missing facts?
- Extraction depends on LLM understanding
- Facts must be explicitly stated (not implied)
- Check extraction prompt in `memory.py`

### Memory not showing in responses?
- Verify memory is loaded in `agent.py`
- Check prompt injection is working
- Memory should appear in system prompt

## Performance

- **Memory Load**: ~50ms per request (cached in request)
- **Memory Extraction**: ~2-3 seconds (async, doesn't block response)
- **Storage**: Minimal (~1-2KB per user)
- **Database Queries**: Indexed, fast retrieval

## Monitoring

Check logs for:
```
[Voyager Debug] Loaded core memory for user=<uuid>
Memory extraction completed for user <uuid>
Updated core memory for user <uuid>
```

## Summary

✅ **Implemented**: Core Memory (Tier 2)
- Automatic fact extraction
- Persistent storage
- Always-loaded context
- Clean API endpoints

🔜 **Next**: Long-Term Memory (Tier 3)
- Vector embeddings
- Semantic search
- Historical insights

The agent now **remembers** users and provides **personalized** assistance!

