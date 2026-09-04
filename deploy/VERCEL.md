# Deploy the Frontend to Vercel

The Next.js 15 frontend is a static-Vercel-compatible build. It talks to the backend via
`NEXT_PUBLIC_API_URL`.

## Prereqs
- A Vercel account + CLI (`npm i -g vercel`).
- The backend deployed (Railway or Docker) and a public HTTPS URL.

## Steps

### Option A — Vercel dashboard
1. Push this repo to GitHub.
2. Import the **`frontend/`** directory as a new project (root directory: `frontend`).
3. Build settings (auto-detected):
   - Build command: `npm run build`
   - Install command: `npm install`
   - Output directory: `.next` (Vercel handles Next.js automatically)
4. Add environment variable:
   - `NEXT_PUBLIC_API_URL` = `https://<your-backend>.up.railway.app`
5. Deploy. The app is served at `https://<your-project>.vercel.app`.

### Option B — CLI
```bash
cd frontend
npm install
vercel --prod --env NEXT_PUBLIC_API_URL=https://<your-backend>.up.railway.app
```

## Notes
- `NEXT_PUBLIC_API_URL` must point to the deployed backend (CORS on the backend must allow
  the Vercel origin `https://<your-project>.vercel.app`).
- Admin dashboard calls `X-Admin-Key`, set `NEXT_PUBLIC_ADMIN_KEY` to match the backend's
  `ADMIN_API_KEY` (only if you're comfortable shipping it client-side; otherwise gate admin
  via your own auth later).