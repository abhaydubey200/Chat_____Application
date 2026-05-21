# Dushman AI

## Provider-Agnostic Multi-Model AI Chat Platform

Dushman AI is a production-ready AI chat platform built with a provider-independent architecture that supports streaming conversations, persistent chat history, and interchangeable LLM providers through a unified backend orchestration layer.

The platform is designed to behave like a scalable AI infrastructure product rather than a simple chatbot wrapper.

---

## Core Features

- ✅ Multi-model AI chat
- ✅ Real-time streaming responses (SSE)
- ✅ Provider abstraction layer
- ✅ Persistent conversations
- ✅ JWT authentication
- ✅ Backend-controlled orchestration
- ✅ Config-driven provider switching
- ✅ Markdown + code rendering
- ✅ Production-oriented architecture
- ✅ Async-first backend design

---

## Architecture Philosophy

Dushman AI follows a strict separation of concerns:

```
Frontend (UI Only)
    ↓
Backend API Layer
    ↓
LLM Router
    ↓
Provider Adapters
    ↓
External LLM Providers
```

The frontend never communicates directly with model providers.
All provider-specific logic is isolated inside adapter layers.

---

## Tech Stack

### Frontend
- Next.js 14+
- Tailwind CSS
- shadcn/ui
- TypeScript

### Backend
- FastAPI
- Python 3.10+
- SQLAlchemy
- asyncpg
- Pydantic

### Database
- PostgreSQL

### AI Providers
- NVIDIA APIs (initial)
- OpenAI (planned)
- Claude (planned)
- Gemini (planned)
- Ollama (planned)

---

## Supported Models

| Purpose | Model | Provider |
|---|---|---|
| Default Chat | Qwen | NVIDIA |
| Fast Responses | Gemma | NVIDIA |
| Reasoning | Nemotron | NVIDIA |

---

## System Architecture

```
Next.js Frontend
    ↓
FastAPI Backend
    ↓
LLM Router Layer
    ↓
Provider Adapter Layer
    ↓
NVIDIA APIs
    ↓
PostgreSQL
```

---

## Repository Structure

```
dushman-ai/
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── store/
│   │   └── utils/
│   ├── public/
│   ├── package.json
│   └── next.config.ts
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── controllers/
│   │   │   ├── routes/
│   │   │   ├── dependencies.py
│   │   │   └── schemas.py
│   │   ├── providers/
│   │   │   ├── base.py
│   │   │   ├── gemini.py
│   │   │   ├── nvidia.py
│   │   │   └── registry.py
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── chat_service.py
│   │   │   └── llm_router.py
│   │   ├── db/
│   │   │   ├── models.py
│   │   │   ├── repositories/
│   │   │   └── init_db.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── security.py
│   │   └── main.py
│   ├── requirements.txt
│   └── .env
│
└── README.md
```

---

## Core Design Principles

### 1. Provider Agnostic Architecture

- No application logic depends directly on any provider API
- Providers are interchangeable through adapter pattern
- Adding new providers requires only new adapter files

### 2. Backend-Controlled Intelligence

The backend controls:
- Model routing
- Streaming protocols
- Retry logic
- Response normalization
- Provider selection

The frontend is presentation-only.

### 3. Config-Driven Provider Switching

Providers can be swapped using environment variables only.

**Example - Switch to OpenAI (future):**
```env
LLM_PROVIDER=openai
LLM_MODEL_DEFAULT=gpt-4-mini
LLM_API_KEY=sk-...
```

**No code rewrites required.** Just update .env

---

## Environment Variables

Create a `.env` file inside the `backend` directory:

```env
# LLM Configuration
LLM_PROVIDER=nvidia
LLM_MODEL_DEFAULT=qwen
LLM_MODEL_FAST=gemma
LLM_MODEL_REASONING=nemotron
LLM_API_KEY=your_api_key

# Database
DATABASE_URL=postgresql://user:password@localhost/dushman_ai

# Security
JWT_SECRET=your_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Application
APP_ENV=development
DEBUG=true
```

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/Prashat090/chat_application.git
cd chat_application
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your API keys and database URL

# Run migrations
python -m alembic upgrade head

# Start backend
uvicorn app.main:app --reload
```

**Backend runs on:** `http://localhost:8000`

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create .env.local (if needed)
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Run development server
npm run dev
```

**Frontend runs on:** `http://localhost:3000`

---

## API Endpoints

### Authentication

```
POST   /auth/signup       - Register new user
POST   /auth/login        - Login user
GET    /auth/me           - Get current user
POST   /auth/logout       - Logout user
```

### Conversations

```
GET    /conversations     - List all conversations
POST   /conversations     - Create new conversation
GET    /conversations/{id} - Get conversation details
PATCH  /conversations/{id} - Update conversation
DELETE /conversations/{id} - Delete conversation
```

### Chat (Streaming)

```
POST   /chat              - Stream chat response (SSE)
GET    /chat/history/{id} - Get conversation history
```

---

## Streaming Architecture

Dushman AI uses **Server-Sent Events (SSE)** for real-time token streaming:

```
Provider Stream
    ↓
Backend Chunk Parser
    ↓
SSE Stream
    ↓
Frontend Renderer
```

**Benefits:**
- Single HTTP connection
- Real-time token delivery
- Lower latency than polling
- Automatic reconnection

---

## Database Schema

### users table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### conversations table
```sql
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### messages table
```sql
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id),
    role VARCHAR(50),
    content TEXT,
    model_used VARCHAR(255),
    provider_used VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Provider Adapter System

Every provider implements a common interface:

```python
from abc import ABC, abstractmethod

class BaseLLMProvider(ABC):
    @abstractmethod
    async def stream_chat(
        self,
        messages: List[Dict],
        model: str,
        temperature: float = 0.7
    ):
        """Stream chat response from provider"""
        pass
    
    @abstractmethod
    async def get_available_models(self) -> List[str]:
        """Get list of available models"""
        pass
```

This enables:
- Provider swapping without code changes
- Unified response handling
- Isolated provider logic
- Easy testing and mocking

---

## Security Features

Dushman AI implements:

- 🔐 JWT token-based authentication
- 🔒 Bcrypt password hashing
- 🔑 Backend-only API key storage
- ✔️ Request validation (Pydantic)
- ⏱️ Rate limiting
- 🛡️ Provider isolation
- 🚫 CORS configuration
- 📝 Input sanitization

---

## Production Deployment

### Frontend
Deploy to:
- **Vercel** (recommended for Next.js)
- Netlify
- AWS Amplify

### Backend
Deploy to:
- **Railway** (easiest)
- **AWS EC2**
- **DigitalOcean**
- **Heroku**
- Self-hosted VPS

### Database
- **Supabase** (PostgreSQL + hosting)
- **AWS RDS**
- **DigitalOcean PostgreSQL**
- Self-hosted PostgreSQL

---

## Production Checklist

The platform is production-ready when:

- ✅ Streaming remains stable under load
- ✅ Provider switching works via config only
- ✅ Conversations persist reliably
- ✅ Backend survives concurrent load
- ✅ Provider abstraction remains intact
- ✅ JWT tokens validated correctly
- ✅ Database connections pooled properly
- ✅ Error handling comprehensive

---

## Current Scope (V1)

### Included
- ✅ Real-time chat
- ✅ SSE streaming
- ✅ Conversation persistence
- ✅ JWT authentication
- ✅ Provider abstraction
- ✅ Multi-model support

### Intentionally Excluded
- ❌ RAG (Retrieval Augmented Generation)
- ❌ Vector databases
- ❌ AI agents
- ❌ Workflows
- ❌ Multimodal AI

*These are planned for future phases.*

---

## Future Roadmap

### Phase 2 (Q3 2026)
- [ ] OpenAI provider
- [ ] Claude provider
- [ ] Advanced observability
- [ ] Better retry systems
- [ ] Request queuing

### Phase 3 (Q4 2026)
- [ ] Local models (Ollama)
- [ ] Distributed inference
- [ ] Enterprise infrastructure
- [ ] Scalable orchestration
- [ ] Vector search

### Phase 4 (2027+)
- [ ] RAG integration
- [ ] Agent framework
- [ ] Workflow engine
- [ ] Multimodal support

---

## Engineering Philosophy

Dushman AI is **NOT** designed as:
- ❌ A chatbot clone
- ❌ An AI agent framework
- ❌ A workflow engine

It is designed as:

> **A provider-independent LLM orchestration platform with conversational UI.**

The chat interface is the **product surface**.

The orchestration layer is the **real system**.

---

## Contributing

Contributions are welcome! Please follow:

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes following code style
3. Test thoroughly
4. Submit pull request

---

## License

MIT License - See LICENSE file for details

---

## Support

- 📧 Email: support@dushman-ai.com
- 💬 Discord: [Coming soon]
- 📖 Docs: [Coming soon]
- 🐛 Issues: GitHub Issues

---

## Final Note

The primary objective of Dushman AI is:

1. **Architectural correctness**
2. **Provider abstraction**
3. **Scalable AI infrastructure design**

The chat interface is the product surface.

**The orchestration layer is the real system.**