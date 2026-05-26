# Dushman AI

## Provider-Agnostic Multi-Model AI Chat Platform

Dushman AI is a production-ready AI chat platform built with a provider-independent architecture that supports streaming conversations, persistent chat history, and interchangeable LLM providers through a unified backend orchestration layer.

The platform is designed to behave like a scalable AI infrastructure product rather than a simple chatbot wrapper.

---

# Core Features

- Multi-model AI chat
- Real-time streaming responses (SSE)
- Provider abstraction layer
- Persistent conversations
- JWT authentication
- Backend-controlled orchestration
- Config-driven provider switching
- Markdown + code rendering
- Production-oriented architecture
- Async-first backend design

---

# Architecture Philosophy

Dushman AI follows a strict separation of concerns:

text Frontend (UI Only)         ↓ Backend API Layer         ↓ LLM Router         ↓ Provider Adapters         ↓ External LLM Providers 

The frontend never communicates directly with model providers.

All provider-specific logic is isolated inside adapter layers.

---

# Tech Stack

## Frontend
- Next.js
- Tailwind CSS
- shadcn/ui
- TypeScript

## Backend
- FastAPI
- Python
- SQLAlchemy
- asyncpg
- Pydantic

## Database
- PostgreSQL

## AI Providers
- NVIDIA APIs (initial)
- OpenAI (future)
- Claude (future)
- Gemini (future)
- Ollama (future)

---

# Supported Models

| Purpose | Model |
|---|---|
| Default Chat | Qwen |
| Fast Responses | Gemma |
| Reasoning | Nemotron |

---

# System Architecture

text Next.js Frontend         ↓ FastAPI Backend         ↓ LLM Router Layer         ↓ Provider Adapter Layer         ↓ NVIDIA APIs         ↓ PostgreSQL 

---

# Repository Structure

text dushman-ai/ │ ├── frontend/ │   ├── app/ │   ├── components/ │   ├── lib/ │   └── styles/ │ ├── backend/ │   ├── api/ │   ├── providers/ │   ├── services/ │   ├── schemas/ │   ├── db/ │   ├── core/ │   └── middleware/ │ ├── docs/ ├── docker/ ├── scripts/ └── README.md 

---

# Core Design Principles

## 1. Provider Agnostic Architecture

No application logic depends directly on any provider API.

Providers are interchangeable.

---

## 2. Backend-Controlled Intelligence

The backend controls:
- model routing
- streaming
- retries
- normalization
- provider selection

The frontend is presentation-only.

---

## 3. Config-Driven Provider Switching

Providers can be swapped using environment variables only.

Example:

env LLM_PROVIDER=nvidia LLM_MODEL_DEFAULT=qwen 

Later:

env LLM_PROVIDER=openai LLM_MODEL_DEFAULT=gpt-5-mini 

No code rewrites required.

---

# Environment Variables

Create a .env file inside the backend directory (see backend/.env.example for the full list).

env # LLM LLM_PROVIDER=nvidia  LLM_MODEL_DEFAULT=qwen LLM_MODEL_FAST=gemma LLM_MODEL_REASONING=nemotron  LLM_API_KEY=your_api_key  # Database DATABASE_URL=postgresql://user:password@localhost/dushman_ai  # Security JWT_SECRET=your_secret JWT_ALGORITHM=HS256  # App APP_ENV=development 

Redis caching (recommended):

env REDIS_ENABLED=true REDIS_URL=redis://localhost:6379/0 REDIS_CACHE_TTL_SECONDS=30 RATE_LIMIT_STORAGE_URL=redis://localhost:6379/1

---

# Local Development Setup

## 1. Clone Repository

bash git clone https://github.com/yourusername/dushman-ai.git cd dushman-ai 

---

## 2. Backend Setup

bash cd backend  python -m venv venv  source venv/bin/activate 

Install dependencies:

bash pip install -r requirements.txt 

Run backend:

bash uvicorn main:app --reload 

---

## 3. Frontend Setup

bash cd frontend  npm install 

Run frontend:

bash npm run dev 

---

## 4. Docker (Full Stack)

bash docker compose up --build

# Streaming Architecture

Dushman AI uses Server-Sent Events (SSE) for real-time token streaming.

Streaming flow:

text Provider Stream     ↓ Backend Chunk Parser     ↓ SSE Stream     ↓ Frontend Renderer 

---

# Database Schema

## users

text id email password_hash created_at 

## conversations

text id user_id title created_at updated_at 

## messages

text id conversation_id role content model_used provider_used created_at 

---

# Provider Adapter System

Every provider implements a common interface:

python class BaseLLMProvider:     async def stream_chat(self, messages, model):         pass 

This enables:
- provider swapping
- unified responses
- isolated provider logic

---

# API Endpoints

## Authentication

http POST /auth/signup POST /auth/login GET  /auth/me 

## Conversations

http GET    /conversations POST   /conversations PATCH  /conversations/{id} DELETE /conversations/{id} 

## Chat

http POST /chat 

---

# Security

Dushman AI includes:

- JWT authentication
- password hashing
- backend-only API keys
- request validation
- rate limiting
- secure provider isolation

---

# Production Deployment

## Frontend
Deploy using:
- Vercel

## Backend
Deploy using:
- Railway
- VPS
- Docker

## Database
- PostgreSQL
- Supabase

---

# Production Goals

The platform is considered production-ready when:

- streaming remains stable
- provider switching works via config only
- conversations persist reliably
- backend survives concurrent load
- provider abstraction remains intact

---

# Current Scope (V1)

Included:
- chat
- streaming
- persistence
- authentication
- provider abstraction

Excluded intentionally:
- RAG
- vector databases
- agents
- workflows
- multimodal AI

---

# Future Roadmap

## Phase 2
- OpenAI provider
- Claude provider
- advanced observability
- better retry systems

## Phase 3
- local models
- distributed inference
- enterprise infrastructure
- scalable orchestration

---

# Engineering Philosophy

Dushman AI is not designed as:
- a chatbot clone
- an AI agent framework
- a workflow engine

It is designed as:

> A provider-independent LLM orchestration platform with conversational UI.

The orchestration layer is the real system.
