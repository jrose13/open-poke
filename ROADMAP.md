# Open Poke Roadmap

## Planned Features

### Benefits Document Reference System
**Status:** Planned  
**Approach:** Tool-based (not sub-agent)

#### Implementation Plan
1. **PDF Ingestion Pipeline**
   - Parse PDF documents → chunk text → generate embeddings
   - Vector storage: In-memory (FAISS) or lightweight vector DB

2. **Search Tool**
   - `search_benefits(query: str)` - semantic search returns relevant sections
   - Context injection: Agent receives benefits context when relevant to user queries

3. **Usage Pattern**
   - Natural inline references during conversation
   - Examples: "what's my copay for X?", "is Y covered?", "what's my deductible?"

#### Rationale for Tool-Based Approach
- Simpler architecture, lower latency
- Natural conversation flow without agent handoffs
- Benefits queries are typically straightforward lookups
- Can refactor to sub-agent later if complexity increases

#### Future Considerations
If insurance queries become complex multi-turn conversations requiring specialized reasoning:
- Consider promoting to "insurance expert" sub-agent
- Would enable specialized prompts for insurance terminology
- Scalable pattern for other experts (pharmacy, claims, etc.)

---

## Memory & Personalization System
**Status:** Research phase

### Current State
We have a basic `user_memories` table in Supabase with simple save/retrieve operations:
- `save_user_memory(user_id, memory_type, content)` 
- `get_user_memories(user_id, memory_type=None)`

However, there's **no sophisticated recall mechanism** - just raw storage. The agent doesn't actively use this memory in conversations.

### Research Findings

#### Industry Memory Architectures

**Three-Tier Memory Model** (General Intelligence Company - Cofounder)
- **Working Memory**: Active workspace for current session/context window
- **Core Memory**: Consolidated session summaries and recent knowledge
- **Long-Term Memory**: Durable organizational knowledge, facts, preferences

**Other Notable Systems:**
- **EgoMem**: Real-time omnimodal recognition, personalized responses, maintains user facts/preferences/relationships
- **Nemori**: Self-organizing episodic memory, learns from prediction gaps
- **Amazon AgentCore Memory**: Extracts meaningful information, consolidates related memories, efficient retrieval
- **HCAM** (Hierarchical Chunk Attention Memory): Divides past into chunks for detailed recall

#### Key Patterns for Implementation

1. **Short-Term Memory (STM)**
   - Lives in context window
   - Current conversation history
   - Volatile - resets after session
   - **What we have now**: Message history in Supabase conversations table

2. **Long-Term Memory (LTM)**
   - Persistent across sessions
   - Stored externally (vector DB, knowledge graphs, structured DB)
   - Retrieved based on relevance to current context
   - **What we need to build**

3. **Memory Management Challenges**
   - Distinguishing signal from noise (important vs. routine chatter)
   - Recognizing related information across time
   - Managing growing memory stores
   - Privacy and security considerations

### Proposed Architecture

#### Tier 1: Working Memory (Current Session)
- Conversation history from current session
- Loaded into agent context window
- Already implemented via Supabase messages table

#### Tier 2: Core Memory (User Profile)
- Structured facts about the user:
  - Name, role (self/caregiver), who they're caring for
  - ZIP code, insurance details
  - Medications, appointments
  - Communication preferences
- Stored in profiles table + user_memories
- **Always loaded** into agent context (compact representation)

#### Tier 3: Long-Term Memory (Episodic/Semantic)
- Past conversation insights and learnings
- User preferences discovered over time
- Historical context and patterns
- **Retrieval-based**: Search and inject relevant memories based on current query

#### Implementation Steps

1. **Phase 1: Core Memory Enhancement**
   - Define structured schema for user facts (name, ZIP, insurance, meds, etc.)
   - Auto-extract and update core memory from conversations
   - Inject core memory into every agent prompt

2. **Phase 2: Semantic Long-Term Memory**
   - Implement vector embeddings for conversation insights
   - Add semantic search for memory retrieval
   - Use FAISS or Supabase pgvector for similarity search

3. **Phase 3: Memory Consolidation**
   - Periodic summarization of conversations into durable insights
   - Detect and merge duplicate/related memories
   - Auto-expire irrelevant or outdated information

4. **Phase 4: Proactive Recall**
   - Agent autonomously retrieves relevant memories based on context
   - Surface memories when useful ("Last time we talked about...")
   - Ask for confirmation/updates on stored facts

### References
- [Amazon AgentCore Memory](https://aws.amazon.com/blogs/machine-learning/building-smarter-ai-agents-agentcore-long-term-memory-deep-dive/)
- [General Intelligence Company - Cofounder Memory System](https://www.generalintelligencecompany.com/writing/introducing-cofounder-our-state-of-the-art-memory-system-in-an-agent)
- [EgoMem: Lifelong Memory for Multimodal Agents](https://arxiv.org/abs/2509.11914)
- [HCAM: Hierarchical Chunk Attention Memory](https://arxiv.org/abs/2105.14039)
- [Nemori: Self-Organizing Memory](https://arxiv.org/abs/2508.03341)

