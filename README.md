# Dushman AI

Provider-agnostic, multi-model AI chat platform with streaming responses, persistent conversation history, and a unified LLM orchestration backend.

## Features
- JWT authentication with signup/login
- Streaming chat via Server-Sent Events (SSE)
- Conversation + message persistence (PostgreSQL)
- Model selection: `default`, `fast`, `reasoning`
- Provider abstraction (NVIDIA default, Gemini optional)
- Rate limiting, request size limits, structured logging
- Optional Redis cache + rate-limit storage
- Markdown + code rendering in the UI

## Tech Stack
| Layer | Tech |
|---|---|
| Frontend | Next.js (App Router), React 19, Tailwind CSS 4, Zustand |
| Backend | FastAPI, SQLAlchemy (async), Pydantic, asyncpg |
| Database | PostgreSQL (local or Supabase) |
| Providers | NVIDIA Inference API, Gemini API |

## Architecture (High-Level)
```
Next.js UI  →  FastAPI API  →  LLM Router  →  Provider Adapters  →  External LLMs
```

Full details: [ARCHITECTURE.md](ARCHITECTURE.md)

## Project Structure
```
Chat_Application/
├── backend/
│   ├── app/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── run-app.bat
└── ARCHITECTURE.md
```

## Local Development

### Prerequisites
- Python 3.10+
- Node.js 20+
- PostgreSQL database (local or Supabase)

### Backend
1. Copy environment file:
   ```bash
   cd backend
   # Windows
   copy .env.example .env
   # macOS/Linux
   cp .env.example .env
   ```
2. Install dependencies and run:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

The frontend uses `NEXT_PUBLIC_API_URL` (default `http://localhost:8000/api`).

### One-Command Windows Start
```bash
run-app.bat
```

## Configuration (Backend)
Create `backend/.env` using `.env.example`. Key settings:

| Variable | Purpose |
|---|---|
| `APP_ENV` | `development` or `production` |
| `PROJECT_NAME` | Display name |
| `JWT_SECRET` | JWT signing secret (min 32 chars) |
| `DATABASE_URL` | `postgresql+asyncpg://...` |
| `LLM_PROVIDER` | `nvidia` or `gemini` |
| `NVIDIA_API_KEY` | Required if `LLM_PROVIDER=nvidia` |
| `GEMINI_API_KEY` | Required if `LLM_PROVIDER=gemini` |
| `CORS_ORIGINS` | Comma-separated frontend origins |
| `REDIS_ENABLED` | `true/false` |
| `REDIS_URL` | Required when Redis is enabled |
| `RATE_LIMIT_STORAGE_URL` | Optional separate Redis DB |

Provider model mappings:
```
NVIDIA_MODEL_DEFAULT
NVIDIA_MODEL_FAST
NVIDIA_MODEL_REASONING
GEMINI_MODEL_DEFAULT
GEMINI_MODEL_FAST
GEMINI_MODEL_REASONING
```

## API Endpoints (Base: `/api`)
| Category | Endpoints |
|---|---|
| Auth | `POST /auth/signup`, `POST /auth/login`, `GET /auth/me` |
| Conversations | `GET /conversations`, `POST /conversations`, `GET /conversations/{id}`, `PATCH /conversations/{id}`, `DELETE /conversations/{id}` |
| Chat | `POST /chat` (SSE stream) |
| Health | `GET /health` |

## Docker (Optional)
Build and run all services (Redis, backend, frontend):
```bash
docker compose up --build
```

## Notes
- Streaming uses SSE; the frontend parses `delta`, `done`, and `error` events.
- Production requires `CORS_ORIGINS` to be set.
- The backend refuses to start if required secrets are missing.
