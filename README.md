# CX Assist — AI-Powered CX Reply Assistant

A **production-grade, deployable AI customer-support reply assistant** built for the
DataStraw Tech Lead Assessment. It demonstrates **Tech-Lead-level decisions** — modular
architecture, strict guardrails, brand isolation, reproducibility (Docker), and a full
human-in-the-loop review flow — not just a demo.

## Non-negotiable guardrails (implemented)

1. **No hallucination** — the LLM receives a strict prompt: *answer only from retrieved
   context; never invent facts.* The response validator re-checks grounding after generation.
2. **No cross-brand leakage** — every search and every document is scoped to a `brand` in
   the vector store `where` clause AND re-validated in the pipeline. It is structurally
   impossible for one brand's policy to answer another brand's customer.
3. **Fallback on missing context** — if no context is retrieved the assistant replies
   verbatim with: *"I couldn't find enough info. Please review manually."* and the reply is
   routed to human review.

## Flow

```
Customer message
  -> brand detect
  -> brand isolation filter
  -> semantic search (ChromaDB, brand-scoped)
  -> context builder
  -> STRICT prompt ("answer only from retrieved context, never hallucinate")
  -> LLM (OmniRoute)
  -> response validator
  -> confidence check
  -> human review: edit / approve / regenerate / manual
  -> send
  -> log
```

Low-confidence or ungrounded replies **always** go to the human review queue; only
high-confidence, grounded replies are eligible to auto-send.

## Tech stack

| Layer     | Choice |
|-----------|--------|
| Frontend  | Next.js 15 (TypeScript, Tailwind), TanStack React Query, React Hook Form |
| Backend   | FastAPI, SQLAlchemy 2, Alembic, Pydantic, repository + DI pattern |
| Database  | PostgreSQL (11 tables), Alembic migrations |
| Vector DB | ChromaDB (HTTP client, brand-scoped `where`) |
| Cache/Ops | Redis (cache, rate limiting, retry queue), request-id middleware, worker |
| LLM       | OmniRoute (primary) + Gemini (fallback); embeddings via local hash or endpoint |
| Auth      | JWT + bcrypt, role-based (admin / agent) |
| Deploy    | Docker / docker-compose; Vercel (frontend), Railway (backend) |

## Repository layout

```
backend/
  app/
    api/         # routers: auth, brands, conversations, replies, review, search, knowledge, orders, admin
    core/        # config, logging, security, guardrails, redis_client, request_id, container (DI)
    db/          # engine/session, base
    models/      # 11 tables: users, brands, brand_sources, knowledge_base, embeddings, customers, orders, conversations, messages, ai_logs, audit_logs
    repositories/  # repository pattern per aggregate
    schemas/     # pydantic
    services/    # embeddings, vector_store, llm (fallback), prompt_builder, crawler, chunker, brand_detect, reranker
    workers/     # background job/retry worker
    main.py      # app entrypoint (request-id middleware, lifespan worker)
    seed.py      # demo brand + knowledge seeding
  alembic/       # migrations (full schema)
frontend/
  app/           # Next.js pages: dashboard, brands, reply, review, knowledge, conversations, login, replying
  components/    # nav, react-query provider
  lib/api.ts     # typed API client + auth token handling
deploy/          # deployment manifests/docs
docker-compose.yml
```

### API summary

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/auth/register` / `/api/auth/login` / `/api/auth/me` | JWT auth |
| POST | `/api/brands` · GET/PATCH/DELETE `/api/brands/{id}` | Brand CRUD (core) |
| GET | `/api/brands/detect?query=` | Brand detection |
| POST | `/api/conversations/generate` | Full reply pipeline (auto / human_review) |
| GET | `/api/conversations/{id}/history` | Conversation history for context |
| GET | `/api/review` · POST `/api/review/{id}/decide` | Human review (approve/edit/regenerate/manual/send) |
| GET | `/api/replies` | Reply audit log |
| POST | `/api/search` | Brand-scoped semantic search |
| POST | `/api/knowledge/chunks` · `/api/knowledge/documents` | Manual KB CRUD (core) |
| GET | `/api/knowledge/brand/{id}` | List KB documents per brand |
| POST | `/api/knowledge/crawl` | **Optional** website crawl (async) |
| POST | `/api/orders/lookup` | Order context lookup |
| GET | `/api/admin/stats` `/audit` `/logs` | Metrics + audit + AI telemetry (admin-key) |
| POST | `/api/admin/webhook` | Optional webhook receiver |

## Manual Brand CRUD is CORE, crawler is OPTIONAL

Per the recommendation, brand + knowledge management is manual-first:
- `/api/auth/register` → create an admin/agent account, then `/api/auth/login` for a JWT.
- `/api/brands` — full CRUD (the admin panel's core).
- `/api/knowledge/documents` + `/api/knowledge/brand/{id}` — manually create, review, edit,
  and delete policy documents in-app (no code/DB changes needed). This is the **default
  workflow**.
- `/api/knowledge/crawl` — **optional** website crawler (fetch → clean → extract → chunk →
  index), running in the background worker queue. Clearly separated so it can be disabled.

## Architecture diagram

See [`deploy/ARCHITECTURE.md`](deploy/ARCHITECTURE.md).

## Quickstart (local, Docker)

```bash
cp .env.example .env      # set OMNIPATH_API_KEY / GEMINI_API_KEY and secret keys
docker compose up --build
```

- Frontend: http://localhost:3000 · Backend API + Swagger: http://localhost:8000/docs
- Compose runs `postgres`, `chromadb`, `redis`, a background `worker`, `backend`, `frontend`.
- The backend container auto-runs migrations + seeds 2 demo brands.

## Run without Docker

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# needs PostgreSQL + ChromaDB running (see docker-compose for the services)
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

## Deployment

- **Frontend → Vercel**: [`deploy/VERCEL.md`](deploy/VERCEL.md), **Backend → Railway**:
  [`deploy/RAILWAY.md`](deploy/RAILWAY.md), **Full config**:
  [`deploy/ARCHITECTURE.md`](deploy/ARCHITECTURE.md).

## Security notes

- JWT auth (bcrypt-hashed passwords) with role-based access (`admin` / `agent`).
- Admin endpoints additionally require `X-Admin-Key` (set `ADMIN_API_KEY`).
- Request-ID on every response (`X-Request-ID`) for end-to-end tracing.
- Redis fixed-window rate limiting on the API.
- CORS restricted to frontend origins; brand isolation enforced structurally + at runtime.
- Brand isolation is enforced at the storage layer, the prompt layer, and the validator.
- All replies are auditable (status, validation code, confidence, context sources, timestamps).