# NYC Dining Concierge — Backend (FastAPI)

Ported 1:1 from the original Streamlit app's business logic — see the top-level
README's "Migration notes" section for what changed vs. the original and why.

## Local development

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in OPENROUTER_API_KEY
uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive OpenAPI docs (every endpoint
below is documented there with live request/response examples).

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | No | Enables real LLM chat via OpenRouter. Unset → `/chat` runs the offline keyword-matching fallback (same as the original app's behavior with no key, not an error state). |
| `ALLOWED_ORIGINS` | Yes in prod | Comma-separated list of origins allowed to call this API (CORS). Must include your deployed Next.js URL. Defaults to `http://localhost:3000`. |
| `DATABASE_PATH` | No | Path to the SQLite file for session-scoped bookmarks/itinerary/imported-dataset storage. Defaults to `./data/app.db`. |

## Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | Liveness check. |
| GET | `/session` | Bootstrap payload: bookmarks, itinerary, active-dataset info. Also sets the `nyc_concierge_session` cookie on first call. |
| POST | `/session/reset` | Mirrors "Reset entire session" — clears bookmarks, itinerary, and any uploaded dataset. Does not re-seed the demo data. |
| POST | `/chat` | `{query, history}` → recommendations. Same two-tier OpenRouter/offline-fallback behavior as the original. |
| GET | `/spots?q=&category=` | Browse/filter the active dataset (demo or uploaded). |
| GET | `/spots/{id}` | Single spot detail. |
| GET/POST | `/bookmarks` | List / add. POST accepts a full spot payload (not just an id) since fallback/LLM spots may not exist in the base dataset. |
| DELETE | `/bookmarks/{id}` | Remove one. |
| POST | `/bookmarks/reset` | Mirrors "Clear bookmarks". |
| GET/POST | `/itinerary` | List / append a stop. |
| DELETE | `/itinerary/{id}` | Remove one. |
| POST | `/itinerary/reset` | Mirrors "Clear itinerary". |
| POST | `/import` | Multipart file upload — Google Maps CSV export or Google Takeout `Saved Places.json`. Replaces the session's entire active dataset. |
| POST | `/import/reset` | Mirrors "✕ Remove uploaded data" — reverts to the demo dataset. |

## Session model

There is no user auth. Each browser gets an anonymous `session_id` via an
httponly cookie, set on first request. Bookmarks, itinerary, and any uploaded
dataset are scoped to that cookie in SQLite — this is genuinely new
persistence where the original Streamlit app had none (its `st.session_state`
only lived in server memory for one browser tab's connection). See the
top-level README for why this design was chosen over a fully shared/global
store.

## Deployment (Railway, chosen as the default — Render/Fly.io work too)

1. Push this repo to GitHub (already done if you're reading this in the repo).
2. On [railway.app](https://railway.app), **New Project → Deploy from GitHub repo**, select this repo, and set the **root directory** to `backend/`.
3. Railway auto-detects Python; set the start command explicitly if it doesn't:
   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
4. Add environment variables in Railway's dashboard: `OPENROUTER_API_KEY`, `ALLOWED_ORIGINS` (your Vercel frontend URL, e.g. `https://your-app.vercel.app`).
5. **Persistence note:** Railway's filesystem is ephemeral on redeploy unless you attach a volume. For a demo/portfolio app this is usually fine (bookmarks/itinerary reset on redeploy, same spirit as the original app having no persistence at all) — attach a Railway Volume mounted at `backend/data` if you want the SQLite file to survive redeploys.
6. Copy the deployed backend URL (e.g. `https://your-app.up.railway.app`) into the frontend's `NEXT_PUBLIC_API_URL`.

Render or Fly.io work the same way (Python buildpack/Dockerfile, same env
vars, same `uvicorn main:app --host 0.0.0.0 --port $PORT` start command) if
you'd rather use one of those instead.
