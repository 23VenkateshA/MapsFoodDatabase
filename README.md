# NYC Dining Concierge

A Streamlit chatbot + map app for querying a curated list of NYC restaurants and bars.
Ask for a vibe, neighborhood, or occasion; get back structured recommendation cards synced
to an interactive Folium map, with bookmarking and light itinerary building.

## Features

- **Split-screen layout** — chat + recommendation cards on the left, a live Folium map on the right.
- **Structured LLM output** — recommendations come back as strict JSON (name, rating, price,
  match highlight, coordinates, links, itinerary context).
- **Saved-first matching** — the assistant checks your curated `data/places.json` list first,
  and only falls back to general NYC knowledge when there aren't enough good matches (flagging
  `fallback_triggered` and using your saved favorites to anchor the style of any fallback picks).
- **Bookmarking & itinerary** — toggle spots as bookmarks, add them to a running itinerary with
  best time slots and durations, manage both from the sidebar.
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

Edit `.env` and set `OPENAI_API_KEY` (preferred) or `ANTHROPIC_API_KEY`. Leave both blank to run
in offline keyword-matching mode.

Run the app:

```bash
streamlit run app.py
```

## Data enrichment

`data/places.json` ships with 9 seed NYC spots. To add more places from a plain list of names
(and optional URLs):

```bash
python enrich_places.py --input raw_places.csv --output data/places.json
```

Input can be CSV (`name,url` columns) or JSON (`[{"name": ..., "url": ...}]`). If
`GOOGLE_PLACES_API_KEY` is set in `.env`, the script fetches real coordinates, ratings, price
levels, and addresses from the Google Places API. Without a key, it generates deterministic,
reasonable placeholder metadata so the pipeline still works fully offline — re-run it later with
a key to upgrade the data in place.

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
