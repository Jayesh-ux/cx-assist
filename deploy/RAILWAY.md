# Deploy the Backend + Data Stores to Railway

Railway runs the FastAPI backend and can host the PostgreSQL + ChromaDB datastores.

## Option A — Railway dashboard (recommended)

1. **Create services** from the `backend/` directory (Dockerfile) and add:
   - **PostgreSQL** plugin → Railway provisions a DB; copy its internal `DATABASE_URL`.
   - **ChromaDB** → run the `chromadb/chroma` image as a service, or use Chroma's managed Cloud.

2. **Environment variables** on the backend service (see `.env.example`):
   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | Railway's `postgres://...` (convert to `postgresql+psycopg2://...`) |
   | `CHROMA_HOST` / `CHROMA_PORT` / `CHROMA_HTTP` | reachable Chroma address |
   | `OMNIPATH_API_KEY` | OmniRoute API key |
   | `ADMIN_API_KEY` | long random secret |
   | `CORS_ALLOW_ORIGINS` | your Vercel origin (defaults include localhost) |

3. Railway runs the Dockerfile `ENTRYPOINT` → which:
   `alembic upgrade head` → `python -m app.seed` → `uvicorn` (auto migrate + seed).

4. **Networking**: expose port `8000` publicly → Railway gives `https://<name>.up.railway.app`.

## Option B — Docker manually (same as local, remote host)
```bash
cp .env.example .env        # fill in real values
docker compose up --build -d db chromadb backend
```

## Notes
- **CORS**: set the backend's allowed origins to `https://<your-frontend>.vercel.app`, or
  keep localhost for local dev.
- **Persistence**: Railway Postgres persists; give Chroma a persistent volume (Railway
  volume or Chroma Cloud) or re-index via `/api/ingest` after restarts.
- **Migrations**: idempotent — safe to run on every deploy via the entrypoint.