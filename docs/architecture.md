# Architecture Guide

Technical overview of the LinkedIn Response Automator system design, RAG pipeline, multi-tenant architecture, and request flow.

## System Overview

The LinkedIn Response Automator consists of two main components:

### Frontend: Chrome Extension

A Chrome extension that runs on LinkedIn.com and provides the user interface for reply generation.

**Responsibilities**:
- Detect when user opens a message or comment thread
- Scrape conversation history from LinkedIn page
- Display "Generate Reply" UI element in compose area
- Submit requests to backend API
- Receive and display suggested replies
- Allow users to edit, accept, or reject suggestions
- Submit feedback on user edits back to backend

**Technologies**:
- Vanilla JavaScript (no frameworks)
- Chrome Extension API for messaging and storage
- Manifest V3 (latest Chrome extension standard)

### Backend: FastAPI Service

A FastAPI REST API that handles reply generation using RAG and Claude AI.

**Responsibilities**:
- Authenticate requests via API keys
- Retrieve conversation history from requests
- Query ChromaDB for similar historical conversations
- Generate embeddings for semantic search
- Call Claude API for reply generation
- Store feedback for continuous learning
- Serve health checks and OpenAPI documentation
- Multi-tenant data isolation per client

**Technologies**:
- FastAPI web framework
- ChromaDB vector database
- Sentence Transformers for embeddings
- Anthropic Claude API for LLM
- Pydantic for data validation
- python-json-logger for structured logging

## Multi-Tenant Architecture

The system is designed to support multiple clients (users/teams) with complete isolation:

```
┌─────────────────────────────────────────────────────────────┐
│                    LinkedIn Response Automator               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐      ┌──────────────────┐             │
│  │   Client A       │      │   Client B       │             │
│  │  (User: alice)   │      │  (User: bob)     │             │
│  │                  │      │                  │             │
│  │ Chrome Extension │      │ Chrome Extension │             │
│  │ API Key: key_a   │      │ API Key: key_b   │             │
│  └──────────────────┘      └──────────────────┘             │
│           │                         │                        │
│           │   POST /generate-reply  │                        │
│           │   + API Key Header      │                        │
│           └─────────┬───────────────┘                        │
│                     ▼                                         │
│           ┌─────────────────────┐                            │
│           │  FastAPI Backend    │                            │
│           │  - Authentication   │                            │
│           │  - Request Routing  │                            │
│           │  - RAG Pipeline     │                            │
│           └──────────┬──────────┘                            │
│                      │                                        │
│         ┌────────────┴────────────┐                          │
│         ▼                         ▼                          │
│  ┌─────────────────┐      ┌─────────────────┐               │
│  │ ChromaDB        │      │  Anthropic API  │               │
│  │                 │      │  (Claude)       │               │
│  │ Client A        │      │                 │               │
│  │ Collection:     │      │ For both        │               │
│  │ "conversations_ │      │ clients         │               │
│  │  alice"         │      │ (shared LLM)    │               │
│  │                 │      │                 │               │
│  │ 1,000 docs      │      └─────────────────┘               │
│  ├─────────────────┤                                         │
│  │ Client B        │                                         │
│  │ Collection:     │                                         │
│  │ "conversations_ │                                         │
│  │  bob"           │                                         │
│  │                 │                                         │
│  │ 800 docs        │                                         │
│  └─────────────────┘                                         │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Data Isolation

- **API Keys**: Each client has unique bearer token in `API_KEYS` environment variable
- **ChromaDB Collections**: Each client stores vectors in separate named collection
- **Configuration**: Per-client settings in `client_configs.json` (tone, context, etc.)
- **Feedback Data**: Feedback stored with `client_id` metadata, query restricted to client collection

**Security Model**:
- Client A can only access their own collection and configuration
- Client B cannot see Client A's historical conversations or feedback
- All queries filtered by client_id in metadata
- Authentication middleware verifies API key before processing

## RAG Pipeline

The Retrieval Augmented Generation (RAG) pipeline retrieves relevant historical conversations and uses them as context for reply generation.

### RAG Flow Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    Generate Reply Request                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Messages:                                              │  │
│  │ - "Hi, are you free next week?"                        │  │
│  │ - "Wednesday works for me"                            │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────┬─────────────────────────────────────────┘
                     ▼
         ┌───────────────────────┐
         │  Extract Search Query  │
         │  "free next week"      │
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────────────────┐
         │  Generate Query Embedding         │
         │  Using Sentence Transformers:     │
         │  all-MiniLM-L6-v2                 │
         │                                   │
         │  Query Vector: [0.12, -0.34, ...]│
         │  (384 dimensions)                 │
         └───────────┬───────────────────────┘
                     ▼
         ┌───────────────────────────────────┐
         │  Semantic Search in ChromaDB       │
         │  (Client-specific collection)     │
         │                                   │
         │  Find 3 most similar conversations│
         │  Using cosine similarity          │
         │                                   │
         │  Scores:                          │
         │  1. 0.89 ✓ "schedule meeting"     │
         │  2. 0.87 ✓ "calendar discussion"  │
         │  3. 0.85 ✓ "time zone question"   │
         └───────────┬───────────────────────┘
                     ▼
         ┌───────────────────────────────────┐
         │  Retrieve Historical Examples      │
         │                                   │
         │  Example 1:                       │
         │  "When is good for you?"          │
         │  → "Tuesday or Wednesday"         │
         │                                   │
         │  Example 2:                       │
         │  "What day works?"                │
         │  → "I'm flexible next week"       │
         │                                   │
         │  Example 3:                       │
         │  "Schedule a call?"               │
         │  → "9 AM EST is ideal for me"     │
         └───────────┬───────────────────────┘
                     ▼
         ┌───────────────────────────────────────────┐
         │  Build Context for LLM                    │
         │                                           │
         │  System Prompt:                           │
         │  "Generate professional LinkedIn replies" │
         │  Tone: {client tone_instructions}        │
         │  Context: {company_context}              │
         │                                           │
         │  User Prompt:                             │
         │  == Examples ==                           │
         │  Q: "When is good for you?"               │
         │  A: "Tuesday or Wednesday"                │
         │  ...                                      │
         │                                           │
         │  == Current Thread ==                     │
         │  "Hi, are you free next week?"            │
         │  "Wednesday works for me"                 │
         │                                           │
         │  == Task ==                               │
         │  Reply to the last message                │
         └───────────┬───────────────────────────────┘
                     ▼
         ┌───────────────────────────────────────────┐
         │  Call Claude API                          │
         │  Model: claude-sonnet-4-20250514          │
         │  Max Tokens: 150                          │
         │  Temperature: 0.4                         │
         │                                           │
         │  ┌─────────────────────────────────────┐  │
         │  │ API Request                         │  │
         │  │ (with system prompt + examples +    │  │
         │  │ current conversation)               │  │
         │  └─────────────────────────────────────┘  │
         │                                           │
         │  ┌─────────────────────────────────────┐  │
         │  │ API Response                        │  │
         │  │ Generated Reply:                    │  │
         │  │ "Perfect! Thursday at 2 PM works   │  │
         │  │ best for me. Looking forward to    │  │
         │  │ our conversation."                 │  │
         │  └─────────────────────────────────────┘  │
         └───────────┬───────────────────────────────┘
                     ▼
         ┌───────────────────────────────────────────┐
         │  Return Reply to Extension                │
         │                                           │
         │  Status: 200 OK                           │
         │  Body: {"reply": "Perfect! Thursday..."}  │
         └─────────────────────────────────────────── ┘
```

### Key Components

**1. Query Encoding**
- Entire current conversation concatenated into string
- Encoded to 384-dimensional embedding using all-MiniLM-L6-v2
- Fast operation (~50ms)

**2. Semantic Search**
- ChromaDB performs cosine similarity search
- Returns top 3 most similar historical conversations
- Searches only client's collection (data isolation)

**3. Context Construction**
- Selected examples embedded in system/user prompts
- Current conversation also included for context
- LLM sees both examples and real conversation
- Helps LLM match tone and style of examples

**4. Reply Generation**
- Claude API called with full context
- Temperature 0.4 (creative but not random)
- Max 150 tokens (~2-3 sentences)
- Enforces constraints: no "Great/Sure", max 3 sentences, professional tone

## Feedback Loop

User feedback continuously improves the system by adding user-edited replies to the training dataset.

### Feedback Flow

```
┌──────────────────────────────────────────────┐
│   Generated Reply from AI                    │
│   "Thursday at 2 PM works well for me"       │
└───────────┬──────────────────────────────────┘
            ▼
┌──────────────────────────────────────────────┐
│  Extension: User sees suggestion              │
│  Options: [Insert] [Edit] [Reject]            │
└───────────┬──────────────────────────────────┘
            ▼
┌──────────────────────────────────────────────┐
│  User Edits the Reply                         │
│  "Thursday at 2 PM works best! Really        │
│   looking forward to our conversation"       │
└───────────┬──────────────────────────────────┘
            ▼
┌──────────────────────────────────────────────┐
│  POST /feedback                               │
│  {                                            │
│    conversation_id: "conv_123",              │
│    original_draft: "Thursday at 2 PM...",    │
│    final_sent_message: "Thursday at 2...",   │
│    was_edited: true,                         │
│    conversation_context: {messages: [...]}   │
│  }                                            │
└───────────┬──────────────────────────────────┘
            ▼
┌──────────────────────────────────────────────┐
│  Backend Background Task                      │
│  1. Extract full context:                     │
│     "Hi, are you free next week?"            │
│     "Wednesday works for me"                 │
│     "Thursday at 2 PM works best!..."        │
│                                              │
│  2. Encode full conversation to embedding    │
│                                              │
│  3. Add to ChromaDB:                         │
│     - Document ID: feedback_conv_123        │
│     - Embedding: [...384 dims...]           │
│     - Metadata: {source: feedback,          │
│       client_id: client_a, timestamp: ...}  │
└───────────┬──────────────────────────────────┘
            ▼
┌──────────────────────────────────────────────┐
│  Future Requests                              │
│  Similar conversations now retrieve           │
│  this feedback example                        │
│  improving future replies                    │
└──────────────────────────────────────────────┘
```

### Benefits

- **Learning**: System learns from actual user replies
- **Personalization**: Captures company/user tone over time
- **Quality Improvement**: More examples = better suggestions
- **Continuous Refinement**: No model retraining needed (semantic search adapts)

## Request Flow Diagram

Complete request journey through the system:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  LINKEDIN TAB                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ User opens message thread:                              │   │
│  │ "Hi! Are you interested in a quick call?"             │   │
│  │ "Sure, when works for you?"                           │   │
│  │                                                         │   │
│  │ [Reply compose box appears]                           │   │
│  │ ┌─────────────────────────────────────────────────┐  │   │
│  │ │ Write your reply here...      [🔧 Generate]     │  │   │
│  │ └─────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼ (User clicks "Generate")            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  CONTENT_SCRIPT.JS (Chrome Extension Content Script)           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. Detect click on Generate button                     │   │
│  │ 2. Scrape conversation from LinkedIn page:            │   │
│  │    - Sender names                                      │   │
│  │    - Message text                                      │   │
│  │    - Message order (chronological)                     │   │
│  │                                                         │   │
│  │ 3. Build request object:                              │   │
│  │    {                                                   │   │
│  │      messages: [                                       │   │
│  │        {sender: "Client", text: "..."},               │   │
│  │        {sender: "You", text: "Sure..."}               │   │
│  │      ]                                                │   │
│  │    }                                                   │   │
│  │                                                         │   │
│  │ 4. Retrieve config from Chrome storage:               │   │
│  │    - apiEndpoint: "http://localhost:8000"             │   │
│  │    - clientId: "default"                              │   │
│  │    - apiKey: "dev_key_12345"                          │   │
│  │                                                         │   │
│  │ 5. POST to backend with Authorization header          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  NETWORK REQUEST                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ POST /generate-reply HTTP/1.1                          │   │
│  │ Host: localhost:8000                                   │   │
│  │ Authorization: Bearer dev_key_12345                    │   │
│  │ Content-Type: application/json                         │   │
│  │                                                         │   │
│  │ {                                                       │   │
│  │   "messages": [                                         │   │
│  │     {"sender": "Client", "text": "Hi! Are you..."},   │   │
│  │     {"sender": "You", "text": "Sure, when works..."}  │   │
│  │   ]                                                     │   │
│  │ }                                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  FASTAPI BACKEND                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │  1. AUTHENTICATION (middleware)                        │   │
│  │     ├─ Extract bearer token: "dev_key_12345"          │   │
│  │     ├─ Check against API_KEYS environment             │   │
│  │     ├─ Verify: {default: "dev_key_12345", ...}       │   │
│  │     └─ Extract client_id: "default" ✓ PASS            │   │
│  │                                                         │   │
│  │  2. CONVERSATION STAGE DETECTION                       │   │
│  │     ├─ Analyze conversation history                   │   │
│  │     ├─ Call Claude API with stage detection prompt    │   │
│  │     └─ Result: "PROPOSAL" (client offering call)      │   │
│  │                                                         │   │
│  │  3. LOAD CLIENT CONFIGURATION                          │   │
│  │     ├─ Read client_configs.json                       │   │
│  │     ├─ Find "default" client config                   │   │
│  │     └─ Load: tone_instructions, company_context       │   │
│  │                                                         │   │
│  │  4. BUILD QUERY FOR SEMANTIC SEARCH                    │   │
│  │     ├─ Concatenate all messages: "Hi! Are you...",   │   │
│  │     │  "Sure, when works..."                          │   │
│  │     └─ Query text: "Hi Are you interested call..."    │   │
│  │                                                         │   │
│  │  5. GENERATE QUERY EMBEDDING                           │   │
│  │     ├─ Load Sentence Transformers model               │   │
│  │     │  (all-MiniLM-L6-v2)                             │   │
│  │     ├─ Encode query to 384-dim vector                 │   │
│  │     └─ Query embedding: [0.123, -0.456, ...]         │   │
│  │                                                         │   │
│  │  6. RAG: SEMANTIC SEARCH IN CHROMADB                   │   │
│  │     ├─ Get client collection: "linkedin_conversations"│   │
│  │     ├─ Query with embedding (cosine similarity)       │   │
│  │     ├─ Retrieve top 3 similar conversations:          │   │
│  │     │  - "When is good?" → "Tuesday PM"              │   │
│  │     │  - "Schedule call?" → "Next week works"        │   │
│  │     │  - "Available?" → "2-4 PM EST"                 │   │
│  │     └─ Filter: only client_id="default" matches       │   │
│  │                                                         │   │
│  │  7. CONSTRUCT CLAUDE PROMPT                            │   │
│  │     ├─ System prompt: tone + company context          │   │
│  │     ├─ User prompt contains:                          │   │
│  │     │  - Historical examples (from step 6)            │   │
│  │     │  - Current thread (from request)                │   │
│  │     │  - Task: "Reply to {last_sender}"              │   │
│  │     └─ Request ID: a1b2c3d4 (for tracing)            │   │
│  │                                                         │   │
│  │  8. CALL ANTHROPIC CLAUDE API                          │   │
│  │     ├─ Model: claude-sonnet-4-20250514                │   │
│  │     ├─ Max tokens: 150                                │   │
│  │     ├─ Temperature: 0.4                               │   │
│  │     ├─ Request body: {system, messages, model, ...}  │   │
│  │     ├─ Log: "Generating reply", request_id, stage    │   │
│  │     └─ Wait for response (~1-3s)                      │   │
│  │                                                         │   │
│  │  9. EXTRACT REPLY TEXT                                 │   │
│  │     ├─ Claude response: {content: [...], stop_reason}│   │
│  │     ├─ Extract text: "Tuesday afternoon works great"  │   │
│  │     └─ Validate: not empty, under 150 tokens         │   │
│  │                                                         │   │
│  │  10. LOG COMPLETION                                    │   │
│  │     ├─ Stage: "api_call_complete"                     │   │
│  │     ├─ Client ID: "default"                           │   │
│  │     ├─ Request ID: "a1b2c3d4"                         │   │
│  │     └─ Log as JSON: {timestamp, level, message, ...}  │   │
│  │                                                         │   │
│  │  11. RETURN RESPONSE                                   │   │
│  │     └─ 200 OK with reply in JSON                      │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  HTTP RESPONSE                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 200 OK                                                  │   │
│  │ Content-Type: application/json                          │   │
│  │ X-Request-ID: a1b2c3d4                                 │   │
│  │                                                         │   │
│  │ {                                                       │   │
│  │   "reply": "Tuesday afternoon works great for me.      │   │
│  │    Looking forward to connecting!"                      │   │
│  │ }                                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  EXTENSION RECEIVES RESPONSE                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Parse JSON response                                     │   │
│  │ Extract reply text                                      │   │
│  │ Display reply in dropdown/popup UI                      │   │
│  │ Show options: [Insert] [Edit] [Reject]                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
└─────────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┼───────────┐
                ▼           ▼           ▼
        ┌────────────┐ ┌────────────┐ ┌────────────┐
        │  INSERT    │ │   EDIT     │ │  REJECT    │
        ├────────────┤ ├────────────┤ ├────────────┤
        │ - Inject   │ │ - User     │ │ - Discard  │
        │   reply    │ │   modifies │ │ - No POST  │
        │   into     │ │ - User     │ │   feedback │
        │   compose  │ │   accepts  │ │ - Done     │
        │   box      │ │ - POST to  │ │            │
        │ - Done     │ │   /feedback│ │            │
        │            │ │ - Done     │ │            │
        └────────────┘ └────────────┘ └────────────┘
```

## Technology Stack

### Frontend
- **HTML5 / CSS3 / Vanilla JavaScript**: No dependencies for simplicity
- **Chrome Extension API**: messaging, storage, content scripts
- **Manifest V3**: Latest Chrome extension standard

### Backend
- **FastAPI**: Modern Python web framework with async support
- **Pydantic**: Data validation and serialization
- **ChromaDB**: Vector database for embeddings and similarity search
- **Sentence Transformers**: Pre-trained embedding model (all-MiniLM-L6-v2)
- **Anthropic SDK**: Official Python client for Claude API
- **python-json-logger**: Structured JSON logging
- **uvicorn**: ASGI application server

### DevOps
- **Docker**: Multi-stage production-ready image
- **Python 3.11**: Official slim base image
- **Non-root user**: Security best practice (UID 1000)
- **Volume mounts**: ChromaDB data persistence

## Performance Characteristics

### Latency
- **Embedding generation**: ~50ms (CPU-bound, cached)
- **ChromaDB search**: ~500ms (vector similarity)
- **Claude API call**: ~1-3s (network dependent)
- **Total end-to-end**: ~2-5 seconds

### Throughput
- **Single worker**: ~12 requests/minute (limited by Claude API rate)
- **Multi-worker**: Scales with uvicorn workers (`--workers 2` by default)
- **Concurrent limit**: Depends on Anthropic API plan

### Storage
- **Per client (1000 conversations)**: ~5-10MB in ChromaDB
- **Model cache**: ~350MB (Sentence Transformers, downloaded once)
- **Base image**: ~200MB (python:3.11-slim)

## Security

### Authentication
- Bearer token in `Authorization` header
- Tokens stored in `API_KEYS` environment variable (secrets management)
- Verified on every request via middleware

### Data Isolation
- Client collections separate in ChromaDB
- Metadata filtering by client_id in queries
- No cross-client data sharing

### Secrets Management
- Environment variables (not in code)
- Docker secrets for sensitive data (optional)
- API keys never logged

### Container Security
- Non-root user (appuser, UID 1000)
- Read-only file system (where possible)
- No privileged escalation

## Scalability

### Horizontal Scaling
- Stateless FastAPI service (can run multiple instances)
- Load balancer routes requests to healthy instances
- Shared ChromaDB via volume or remote instance

### Vertical Scaling
- Increase uvicorn workers (`--workers 4`)
- Pre-warm embedding model on startup
- Cache frequently used queries

### Database Scaling
- ChromaDB supports remote servers
- Sharding by client_id across instances
- Regular backups of `/app/data` volume

## Monitoring and Logging

### JSON Structured Logging
- All logs include: timestamp, level, logger, message, extra fields
- Request IDs (UUID4 first 8 chars) track requests end-to-end
- Fields include: client_id, stage, error, request_id for debugging

### Metrics
- Request count and latency per endpoint
- Error rates by client_id
- ChromaDB query latency and cache hit rate

### Health Checks
- Built-in `/health` endpoint (returns `{"status": "ok"}`)
- Docker HEALTHCHECK with curl probe
- Kubernetes liveness/readiness probes supported

## Limitations and Trade-offs

### Current Limitations
- Single Sentence Transformers model (all-MiniLM-L6-v2)
- Fixed max 150 tokens per reply
- No image/link handling in conversations
- Linear RAG (no multi-hop reasoning)

### Design Trade-offs
- Simplicity over advanced features (vanilla JS, no frameworks)
- Local ChromaDB over distributed vector DB (easier deployment)
- Fixed embedding model over fine-tuned (better generalization)
- Temperature 0.4 over variable (consistent tone)

---

**Last Updated**: March 2026  
**Version**: 1.0
