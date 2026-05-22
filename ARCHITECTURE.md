# Dushman AI - Architecture & Design Document

## Overview

Dushman AI is a production-grade, provider-agnostic LLM orchestration platform. It provides a conversational UI with real-time streaming, persistent chat history, and switchable AI providers through unified backend abstraction.

**Key Principle**: The frontend is presentation-only. All intelligence, provider logic, and state management lives in the backend.

---

## Core Architecture Layers

```
┌─────────────────────────────────────────┐
│      Next.js Frontend (UI Only)        │
│  - ChatWindow, MessageBubble             │
│  - Zustand State Management              │
│  - SSE Stream Consumption                │
└────────────┬────────────────────────────┘
             │ HTTP + Server-Sent Events
             ↓
┌─────────────────────────────────────────┐
│      FastAPI Backend API Layer          │
│  - /auth: JWT authentication             │
│  - /conversations: CRUD operations       │
│  - /chat: Streaming SSE endpoint         │
└────────────┬────────────────────────────┘
             │ Orchestration
             ↓
┌─────────────────────────────────────────┐
│      LLM Router Layer                    │
│  - Model type resolution                 │
│  - Provider selection                    │
│  - Response normalization                │
└────────────┬────────────────────────────┘
             │ Provider Abstraction
             ↓
┌─────────────────────────────────────────┐
│      Provider Adapters                   │
│  - NvidiaProvider (active)               │
│  - GeminiProvider (future)               │
│  - Extensible for new providers          │
└────────────┬────────────────────────────┘
             │ HTTP/REST
             ↓
┌─────────────────────────────────────────┐
│      External AI Services                │
│  - NVIDIA Inference API                  │
│  - Google Gemini API                     │
└─────────────────────────────────────────┘
```

---

## Backend Architecture Details

### 1. API Routes (`app/api/routes/`)

#### **auth.py** - Authentication
- `POST /auth/signup` - User registration with email validation
- `POST /auth/login` - JWT token generation
- `GET /auth/me` - Current user profile retrieval
- Dependency: `get_current_user()` validates JWT tokens

#### **conversations.py** - Conversation Management
- `POST /conversations` - Create new conversation (with auto-title)
- `GET /conversations` - List all user conversations (sorted by updated_at DESC)
- `GET /conversations/{id}` - Get conversation with full message history
- `PATCH /conversations/{id}` - Rename conversation
- `DELETE /conversations/{id}` - Delete conversation (cascades to messages)
- Dependency: `get_current_user()` ensures user owns conversation

#### **chat.py** - Streaming Chat
- `POST /chat` - Main streaming endpoint
- Request: `{conversation_id, message, model_type}`
- Response: `EventSourceResponse` (Server-Sent Events)
- Events: `{event: 'delta'|'done'|'error', data: JSON}`
- Rate Limited: 30 requests/minute per client IP

### 2. Controllers (`app/api/controllers/`)

Controllers bridge routes and business logic:

- **auth_controller.py** - Handles user signup/login, password hashing, JWT generation
- **chat_controller.py** - Saves user message, streams LLM response via SSE
- **conversation_controller.py** - CRUD operations on conversations

### 3. Services (`app/services/`)

Business logic layer:

- **auth_service.py**
  - User registration with bcrypt password hashing
  - JWT token creation and validation
  - Session management

- **chat_service.py**
  - `create_user_message()`: Saves user messages with deduplication
  - `stream_chat_response()`: Streams LLM response, accumulates, persists to DB
  - Handles message history loading (limit 40)
  - Injects system prompt for consistent behavior

- **llm_router.py**
  - `resolve_model()`: Maps "default"/"fast"/"reasoning" to concrete model names
  - `stream()`: Routes to provider, injects metadata (provider, model)
  - **No provider-specific logic** - pure routing

### 4. LLM Providers (`app/providers/`)

Abstract adapter pattern for AI services:

- **base.py** - `BaseLLMProvider` interface
  - `stream_chat()` - async generator yielding chunks
  - `chat()` - non-streaming response (for future use)

- **nvidia.py** - NVIDIA API implementation
  - Handles HTTP streaming with timeouts (120s total, 10s per chunk)
  - Parses SSE format: `data: {...}\n\n`
  - Graceful error handling and partial response support
  - No hardcoded models - uses config from settings

- **gemini.py** - Placeholder (not yet implemented)

- **registry.py** - Provider factory
  - Registers all providers at startup
  - `get_provider(name)` returns provider instance

### 5. Database Layer (`app/db/`)

#### **models.py** - SQLAlchemy ORM Models
```
User
├── id: UUID (primary key)
├── email: String (unique)
├── password_hash: String
├── created_at: DateTime
└── conversations: Relationship[Conversation]

Conversation
├── id: UUID (primary key)
├── user_id: UUID (FK → User)
├── title: String
├── created_at: DateTime
├── updated_at: DateTime (on-update trigger)
└── messages: Relationship[Message]

Message
├── id: UUID (primary key)
├── conversation_id: UUID (FK → Conversation)
├── role: String ("user" | "assistant")
├── content: String
├── model_used: String (nullable, e.g., "meta/llama-3.1-70b-instruct")
├── provider_used: String (nullable, e.g., "nvidia")
└── created_at: DateTime
```

#### **database.py** - Connection Management
- Async SQLAlchemy engine with asyncpg driver
- Connection pool: 20 base connections, 40 max overflow
- Pool health checks (pool_pre_ping=True)
- Auto-recycling (3600s) for stale connections
- Dependency injection: `get_db()` yields AsyncSession

#### **repositories/** - Data Access Layer
- **user_repository.py**: User lookup, creation
- **conversation_repository.py**: CRUD with user ownership checks
- **message_repository.py**: Save messages, load history (limited to 40)

### 6. Core Modules (`app/core/`)

- **config.py** - Pydantic settings management
  - Loads from `.env` file
  - Validates all required configs at startup
  - Environment-aware defaults (dev vs. production)

- **database.py** - Connection pool, session factory
  - `verify_database_connection()` - Health check
  - `init_db()` - Create schema on startup
  - `close_db()` - Cleanup on shutdown

- **security.py** - Authentication utilities
  - `get_password_hash()` - Bcrypt hashing
  - `verify_password()` - Constant-time comparison
  - `create_access_token()` - JWT signing
  - `decode_access_token()` - JWT validation

- **dependencies.py** - FastAPI dependencies
  - `get_current_user()` - Extract + validate JWT from Authorization header

---

## Frontend Architecture Details

### 1. State Management (`src/store/chatStore.ts`)

Zustand-based global store with the following structure:

**State:**
- `user` - Current authenticated user
- `token` - JWT access token
- `conversations` - List of all conversations
- `currentConversationId` - Active conversation
- `messages` - Messages in active conversation
- `modelType` - Selected model ("default", "fast", "reasoning")
- `isGenerating` - Streaming in progress flag
- `abortController` - Active stream cancellation handle
- `error` - Last error message

**Actions:**
- `initAuth()` - Restore session from localStorage on app load
- `login()` / `signup()` - Set auth state
- `logout()` - Clear all state
- `fetchConversations()` - Load all conversations
- `createConversation()` - New conversation
- `selectConversation()` - Load conversation + messages
- `renameConversation()` - Update title
- `deleteConversation()` - Delete conversation
- `sendMessage()` - Send + stream response
- `stopGeneration()` - Cancel stream

**Key Design:**
- SSE streaming integrated directly in store (via `streamChat` util)
- Message UUIDs use timestamp + random to prevent collisions
- Conversation switching clears old messages before loading new ones
- Error recovery: removes temp messages on stream failure
- AbortController cleanup: cancels any active streams

### 2. Components (`src/components/`)

**ChatWindow.tsx**
- Main chat interface
- Displays conversations list (sidebar)
- Renders message bubbles
- Input form with send/stop buttons
- Auto-scroll to latest message
- Shows loading indicator and error messages

**MessageBubble.tsx**
- Individual message display
- Role-based styling (user vs. assistant)
- Markdown + code block rendering
- Copy button for code blocks

**ChatSidebar.tsx**
- Lists all conversations
- Active conversation highlighting
- Delete/rename buttons
- Create new conversation button

**ModelSelector.tsx**
- Radio buttons for model selection
- Descriptions of each model type
- Updates store on selection change

### 3. Utilities (`src/utils/`)

**api.ts**
- Generic fetch wrapper with JWT auth
- `apiGet`, `apiPost`, `apiPatch`, `apiDelete` helpers
- `streamChat()` - SSE event stream handler
  - Reads from `response.body` as stream
  - Parses SSE format: `event: type\ndata: {...}\n\n`
  - Handles `delta` (token), `done` (completion), `error` events
  - Supports AbortController for cancellation
  - Reconnection logic: automatic on network errors

---

## Streaming Architecture

### Request Flow
```
User sends message
  ↓
ChatWindow.handleSend()
  ↓
chatStore.sendMessage()
  ├─ Create temp user message (add to state)
  ├─ Create temp assistant message (placeholder)
  ├─ POST /chat with conversation_id, message, model_type
  │  ↓
  │  ChatController.chat()
  │  ├─ Save user message to DB
  │  ├─ Call ChatService.stream_chat_response()
  │  │  ├─ Load conversation history
  │  │  ├─ Inject system prompt
  │  │  ├─ Call llm_router.stream()
  │  │  │  ├─ Resolve model type to concrete model
  │  │  │  ├─ Get provider from registry
  │  │  │  ├─ Call provider.stream_chat()
  │  │  │  │  ├─ Open HTTP stream to NVIDIA/Gemini API
  │  │  │  │  ├─ Parse SSE chunks
  │  │  │  │  └─ Inject metadata (provider, model)
  │  │  │  └─ Yield chunks
  │  │  └─ Accumulate chunks, persist final response to DB
  │  └─ Yield SSE events
  │
  └─ streamChat() SSE reader
     ├─ Read from event stream
     ├─ Parse SSE format
     ├─ Call onChunk() for each delta
     ├─ Update temp assistant message content
     └─ Call onDone() to refresh from DB
```

### SSE Event Format
```
// Token delta
event: delta
data: {"type": "delta", "content": "token", "provider": "nvidia", "model": "..."}

// Stream completion
event: done
data: {"type": "done", "content": "full response text", ...}

// Error
event: error
data: {"type": "error", "content": "error message"}
```

### Timeout & Cancellation
- **Frontend**: AbortController signal sent to fetch()
- **Backend**: Stream generator cleanup on client disconnect
- **Provider**: 120s total timeout, 10s per chunk timeout
- **Fallback**: Returns partial response if interrupted

---

## Configuration & Environment Switching

### Provider Switching (Zero Code Changes)

**To switch from NVIDIA to OpenAI (future):**

1. Update `.env`:
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

2. Backend automatically:
   - Loads OpenAI provider from registry
   - Routes requests to OpenAI
   - No code changes needed
   - Frontend completely unaware

### Model Type Mapping

Abstraction: Apps reference "default"/"fast"/"reasoning"
Provider implementation: Maps to concrete model names

```python
# In config.py and llm_router.py
LLM_PROVIDER=nvidia
NVIDIA_MODEL_DEFAULT=meta/llama-3.1-70b-instruct
NVIDIA_MODEL_FAST=meta/llama-3-8b-instruct
NVIDIA_MODEL_REASONING=nvidia/llama-3.1-nemotron-70b-instruct

# User selects "fast" → router resolves to "meta/llama-3-8b-instruct"
# User selects "reasoning" → router resolves to "nvidia/...nemotron-70b-instruct"
```

---

## Security Model

### Authentication
- **JWT-based**: Signed with HS256 (HMAC-SHA256)
- **Storage**: localStorage (frontend), HTTP-only cookies (future)
- **Validation**: Every protected endpoint verifies JWT

### Data Isolation
- **User ownership checks**: Every query filters by `user_id`
- **Foreign key constraints**: Database enforces relationships
- **Conversation isolation**: Users can only access their conversations

### Password Security
- **Bcrypt hashing**: ~12 rounds by default
- **Strength validation**: Min 8 chars, uppercase + digit
- **Never returned**: Passwords never sent in responses

### API Security
- **CORS restriction**: Only configured origins allowed
- **Rate limiting**: 30 requests/minute per IP on /chat
- **Request size limit**: 2MB max body size
- **Input validation**: Pydantic validates all requests
- **SQL injection prevention**: Parameterized queries (SQLAlchemy ORM)

### Secret Management
- **API keys**: Stored in environment variables, never in code
- **Config validation**: Fails at startup if secrets missing
- **Production enforcement**: CORS_ORIGINS required in production

---

## Scalability Considerations

### Vertical Scaling (Single Server)
- **DB Connection Pool**: 20 base + 40 overflow = handles ~60 concurrent requests
- **Async I/O**: All I/O is non-blocking (asyncio + asyncpg)
- **Memory**: Streaming reduces memory footprint (no full response buffering)
- **Timeouts**: Prevent resource leaks from stalled requests

### Horizontal Scaling (Multiple Servers)
**Future roadmap:**
- Session persistence: Redis for distributed token validation
- Message broker: Queue streaming requests (RabbitMQ/Kafka)
- Load balancer: Distribute across multiple API servers
- Separate DB: PostgreSQL on dedicated server
- Cache layer: Redis for conversation caching

### Provider Rate Limiting
- Currently: 30 requests/minute per IP
- Future: Per-user quotas, provider-specific limits
- Backoff: Exponential backoff on provider errors

---

## Error Handling Strategy

### Frontend
- **Error boundaries**: Catch component crashes, show fallback UI
- **Stream errors**: Partial responses displayed, error shown
- **Auto-retry**: Network errors trigger automatic reconnection
- **User messages**: Plain language, no internal details

### Backend
- **Validation errors**: 400 Bad Request with details
- **Auth errors**: 401/403 with reason
- **Provider errors**: 502 Bad Gateway (provider issue) or 500 (our issue)
- **Logging**: Structured logs with request context

### Database
- **Transaction rollback**: Automatic on any error
- **Connection retry**: Pool health checks + recycling
- **Cascade delete**: Orphaned messages cleaned up

---

## Monitoring & Observability

### Metrics
- Request count and latency
- Streaming success rate
- Provider error rates
- Database query times
- Memory and CPU usage

### Logs
- Structured JSON logs with context
- Request ID for tracing
- Error stack traces
- Provider API calls and responses

### Health Checks
- `/health` endpoint with DB verification
- Startup DB connection test
- Provider availability checks (future)

---

## Deployment Architecture

### Containerization (Future)
```dockerfile
# Backend: FastAPI + asyncpg
FROM python:3.11-slim
COPY backend /app
RUN pip install -r requirements.txt
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]

# Frontend: Next.js
FROM node:18-alpine
COPY frontend /app
RUN npm install && npm run build
CMD ["npm", "start"]
```

### Environment Variables
- `.env` for local development
- `.env.production` for production
- See `backend/.env.example` for all options

### Database Migrations (Future)
- Alembic for schema versioning
- `alembic upgrade head` on deployment
- Automatic on startup (during init_db)

---

## Future Enhancements

### Phase 2
- [ ] Multiple provider support (OpenAI, Claude, Gemini)
- [ ] Message pagination (avoid loading 1000+ messages)
- [ ] Conversation search
- [ ] Message reaction system
- [ ] Scheduled exports

### Phase 3
- [ ] Redis caching layer
- [ ] Message queue (RabbitMQ)
- [ ] Distributed rate limiting
- [ ] Advanced observability (Datadog/Sentry)
- [ ] Multi-tenancy support

### Phase 4
- [ ] RAG (Retrieval Augmented Generation)
- [ ] Document upload & processing
- [ ] Vector embeddings (pgvector)
- [ ] Agent framework
- [ ] Tool calling

---

## Testing Strategy (To Implement)

### Unit Tests
- Provider adapters (mock API responses)
- Chat service logic (with test database)
- Frontend store actions

### Integration Tests
- Full request flow: signup → chat → verify DB
- Provider switching (mock provider registry)
- Streaming completion

### E2E Tests
- User journey: login → create conversation → chat
- Error handling paths
- Edge cases (long messages, many messages, timeouts)

### Load Tests
- Concurrent requests scaling
- Streaming stability under load
- Database connection pool behavior

---

**Last Updated**: May 2026
**Version**: 1.0.0
**Status**: Production-Ready (TIER 1 stabilization complete)
