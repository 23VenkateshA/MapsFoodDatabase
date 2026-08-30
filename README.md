# NYC Dining Concierge

An AI concierge for a curated list of NYC restaurants and bars — chat for recommendations, browse
and filter the full list, bookmark spots, and build a light itinerary, all synced to an interactive
map.

**This repo now has two apps:**

- **`backend/` + `frontend/`** — the current stack: **Next.js (App Router, TypeScript, Tailwind,
  shadcn/ui)** talking to a **FastAPI** backend. Clean Google-Material-style UI, `react-leaflet`
  map with marker clustering.
- **`app.py`** (repo root) — the **original Streamlit + Folium** app this was migrated from. Left
  in place and still deployed at
  https://mapsfooddatabase-bhkjca9anz4utbcinglkux.streamlit.app — see its section below if you
  want to run or retire that version.

## Architecture

```
frontend/  Next.js, deployed on Vercel
   │  fetch() calls, session cookie
   ▼
backend/   FastAPI, deployed on Railway/Render/Fly.io (NOT Vercel — it doesn't
           run long-lived Python processes well)
   │
   ├─ data/places.json      158-spot demo dataset (static, ported as-is)
   ├─ data/app.db           SQLite: session-scoped bookmarks/itinerary/uploads
   ├─ OpenRouter             LLM chat (falls back to offline keyword matching)
   └─ Nominatim (OSM)        free geocoding, used only by the CSV-import path
```

The two services are deployed separately and talk to each other over HTTP —
the frontend never touches Python directly, and the backend has no knowledge
of React.

## Quickstart

**Backend** (see [`backend/README.md`](backend/README.md) for full details):

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add OPENROUTER_API_KEY
uvicorn main:app --reload --port 8000
```

**Frontend**, in a second terminal:

```bash
cd frontend
npm install
cp .env.local.example .env.local   # defaults to http://localhost:8000, fine for local dev
npm run dev
```

Visit `http://localhost:3000`.

## Deployment

| Service | Platform | Required env vars |
|---|---|---|
| `frontend/` | Vercel | `NEXT_PUBLIC_API_URL` → your deployed backend URL |
| `backend/` | Railway (see [`backend/README.md`](backend/README.md); Render/Fly.io work identically) | `OPENROUTER_API_KEY`, `ALLOWED_ORIGINS` → your deployed Vercel URL |

Deploy the backend first, then point the frontend's `NEXT_PUBLIC_API_URL` at it.

## Migration notes (Streamlit → Next.js/FastAPI)

This was a **behavior-preserving framework migration**, not a redesign or a
logic rewrite — ranking, filtering, and duration logic all work exactly as
they did in `app.py`, with one exception noted below.

**Ported 1:1** (same prompt text, same algorithms, same data):
- Chat recommendation logic — system prompt, OpenRouter call, offline
  keyword-match fallback, and the exact try/except provider-selection order.
- Browse/filter substring + category matching.
- CSV/Google-Takeout-JSON import — same Nominatim geocoding, same cuisine
  classification, same synthetic-coordinate fallback.
- The demo dataset (`data/places.json`, unchanged) and the first-load
  auto-seed (same 4 bookmark ids + 1 itinerary id).

**New, because Streamlit provided it implicitly:**
- **Persistence.** The original had none — `st.session_state` lived only in
  server memory for one browser tab's connection. A REST API needs
  *somewhere* to keep bookmarks/itinerary/uploaded-dataset between requests,
  so this now uses a lightweight SQLite store keyed by an anonymous
  `session_id` cookie — closely mirroring the original's per-tab isolation,
  but now surviving backend restarts. Flagged explicitly since it's new
  capability where none existed before, not a like-for-like port.
- **CORS configuration**, explicit loading/error states for every API call
  (chat pending, spots fetch failed, import errors) — Streamlit's
  request/rerun model made these implicit; React needs them spelled out.
- **Client-side dynamic import for the map** — `react-leaflet` touches
  `window` at import time, so `MapView` is loaded with `ssr: false`, the
  direct equivalent of `st_folium` only ever existing in the browser.

**Behavior difference from the original (however minor, flagged so nothing
changed silently):**
- The itinerary duration values had a small pre-existing inconsistency
  between two code paths in `app.py` (75 min in `place_to_spot()` vs. 90 min
  in the offline chat fallback). Per explicit instruction during the
  migration, this was aligned to 75 rather than ported as-is — everything
  else is an exact behavioral match.

## Legacy Streamlit app (`app.py`)

Still fully functional and independently deployed. See the version of this
README before the migration (or just read `app.py`/`enrich_places.py`
directly) for its own quickstart — the short version:

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add OPENROUTER_API_KEY
streamlit run app.py
```

Its own `.env`/`requirements.txt`/`.streamlit/config.toml` are unrelated to
the `backend/`/`frontend/` ones above — the two apps don't share config.
