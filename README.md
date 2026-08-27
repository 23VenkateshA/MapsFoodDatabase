# NYC Dining Concierge

**Live app:** https://mapsfooddatabase-bhkjca9anz4utbcinglkux.streamlit.app

A Streamlit chatbot + map app for querying a curated list of NYC restaurants and bars.
Ask for a vibe, neighborhood, or occasion; get back structured recommendation cards synced
to an interactive Folium map, with bookmarking and light itinerary building.

## Features

- **Split-screen layout** — chat + recommendation cards on the left, a live Folium map on the right.
- **Two view modes** — 💬 Concierge Chat for LLM-curated picks, or 🔎 Browse All Spots to search
  and filter the full 158-place dataset with category chips (Bars / Cafes / Eats) and a free-text
  search box; the map always reflects whichever set of spots is currently active.
- **Structured LLM output** — recommendations come back as strict JSON (name, rating, price,
  match highlight, coordinates, links, itinerary context).
- **Saved-first matching** — the assistant checks your curated `data/places.json` list first,
  and only falls back to general NYC knowledge when there aren't enough good matches (flagging
  `fallback_triggered` and using your saved favorites to anchor the style of any fallback picks).
- **Bookmarking & itinerary** — toggle spots as bookmarks, add them to a running itinerary with
  best time slots and durations, manage both from the sidebar. A few demo bookmarks and one
  itinerary stop are pre-seeded on first load so the app doesn't look empty before you've done
  anything; Clear/Reset in the sidebar work normally afterward and won't re-seed.
- **Bring your own places** — click **📤 Import** to upload your own place list instead of the
  158-spot demo dataset, scoped to your browser session (nothing is written to a database or
  shared with other visitors — it's held in `st.session_state` and lost on a page reload). Two
  formats are supported: a Google Maps list-export CSV (`Title`/`URL` columns — each row is
  geocoded via free OpenStreetMap Nominatim, so a large list takes a while, shown with a progress
  bar), or a Google Takeout `Saved Places.json` export (already has real coordinates, so it
  imports instantly). Click "✕ Remove uploaded data" to go back to the demo dataset.
- **Offline mode** — with no API key configured, the app still runs end-to-end using a
  rule-based keyword matcher against your saved list.

## Quickstart

```bash
cd MapsFoodDatabase
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set `OPENROUTER_API_KEY` (get one at [openrouter.ai](https://openrouter.ai) — it's
OpenAI-API-compatible and can route to many providers/models with one key). Leave it blank to run
in offline keyword-matching mode.

Run the app:

```bash
streamlit run app.py
```

## Data enrichment

`data/places.json` ships with 158 NYC spots (26 bars, 20 cafes, 112 eats), ingested from Google
Maps list exports via `enrich_places.py`. To (re)build it from CSV exports:

```bash
python enrich_places.py \
  --input "Bar:NYC Bars.csv" \
  --input "Cafe:NYC Cafe.csv" \
  --input "Eats:NYC Eats.csv" \
  --output data/places.json
```

A single file also works: `python enrich_places.py --input raw_places.csv --output data/places.json`
(CSV needs a `Title`/`name` column and a `URL` column — this matches Google Maps' own list-export
format). JSON input (`[{"name": ..., "url": ...}]`) works too.

Enrichment runs in tiers, per place:
1. **Google Places API**, if `GOOGLE_PLACES_API_KEY` is set in `.env` — real coordinates, rating,
   price level, and address.
2. **Free OpenStreetMap (Nominatim) geocoding**, no key required — real coordinates and an
   address-derived neighborhood. Rate-limited to ~1 request/sec per Nominatim's usage policy, so
   ingesting ~150 places takes a few minutes.
3. **Offline synthetic fallback** — deterministic placeholder coordinates/neighborhood for
   anything the free geocoder can't resolve (ambiguous chain names, etc.).

Cuisine/type tags are guessed from the place name via keyword matching (e.g. "Taqueria" →
Mexican/Tacos). Rating, price level, and happy-hour info are estimated placeholders unless a
Google Places key is set — they're not verified facts, so treat them as a starting point. Entries
sharing a name but pointing at different Google Maps URLs (e.g. multiple locations of the same
chain) are kept as separate spots but may share a geocoded location, since the free geocoder only
has the name to go on.

## Project structure

```
MapsFoodDatabase/
├── app.py                  # Main Streamlit application
├── enrich_places.py        # Data enrichment CLI (Google Places API or offline fallback)
├── data/
│   └── places.json         # Curated seed dataset of NYC venues
├── requirements.txt
├── .env.example
└── README.md
```

## Notes

- Map pins: 🔵 blue = spots sourced from your saved list, 🟢 green = general-knowledge fallback picks.
- Chat history, bookmarks, and itinerary all live in `st.session_state` and reset when you use the
  sidebar's "Reset entire session" button or restart the app.
