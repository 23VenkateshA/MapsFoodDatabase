"""NYC Dining Concierge - Streamlit app.

Split-screen chatbot + map for querying a curated NYC restaurant list.
Left column: chat + structured recommendation cards. Right column: synced
Folium map. Sidebar: bookmarks + itinerary management.
"""

import csv
import io
import json
import os
import re
import time
from pathlib import Path

import folium
import requests
import streamlit as st
from dotenv import load_dotenv
from streamlit_folium import st_folium

import enrich_places

load_dotenv()

DATA_PATH = Path(__file__).parent / "data" / "places.json"
NYC_CENTER = (40.7295, -73.9965)
BROWSE_CARD_LIMIT = 40
CATEGORY_CHIPS = [("All", "All"), ("Bars", "Bar"), ("Cafes", "Cafe"), ("Eats", "Eats")]
SEED_BOOKMARK_IDS = ["212-east", "wiggle-room", "the-bean", "mahmoud-s-corner-halal-food-cart"]
SEED_ITINERARY_ID = "cello-s-pizzeria"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = "openai/gpt-4o-mini"

st.set_page_config(page_title="NYC Dining Concierge", page_icon="🍽️", layout="wide")


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@st.cache_data
def load_places(_cache_key):
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def init_state(saved_places):
    seed_bookmarks = {p["id"]: place_to_spot(p) for p in saved_places if p["id"] in SEED_BOOKMARK_IDS}
    seed_itinerary = [place_to_spot(p) for p in saved_places if p["id"] == SEED_ITINERARY_ID]

    defaults = {
        "messages": [],
        "bookmarks": seed_bookmarks,
        "itinerary": seed_itinerary,
        "last_spots": [],
        "last_summary": "",
        "last_filters": [],
        "pending_query": None,
        "view_mode": "chat",
        "browse_query": "",
        "browse_category": "All",
        "uploaded_places": None,
        "upload_status": None,
        "_last_upload_sig": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ---------------------------------------------------------------------------
# LLM orchestration
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = """You are the NYC Dining Concierge, a chatbot that recommends NYC \
restaurants and bars based on the user's request.

You have access to the user's SAVED SPOTS list below. Always check this list first.

SAVED SPOTS (JSON):
{saved_places_json}

Rules:
1. Primary match: prefer spots from SAVED SPOTS that fit the user's request.
2. Fallback: if fewer than 2-3 saved spots clearly match, add well-known NYC restaurants/bars \
from your general knowledge that fit the request. Set "fallback_triggered": true whenever you \
add any non-saved spot, and set that spot's "source" to "fallback".
3. Lookalike anchoring: when you add fallback spots, favor ones stylistically similar to the \
user's saved favorites (similar price level, vibe, or cuisine).
4. Always respond with STRICT JSON matching this schema, and nothing else - no markdown fences, \
no commentary:

{{
  "summary": "1-2 sentence overview explaining the matches found.",
  "fallback_triggered": false,
  "spots": [
    {{
      "id": "spot-slug",
      "name": "Restaurant Name",
      "source": "saved | fallback",
      "is_bookmarked": false,
      "neighborhood": "East Village",
      "cuisine": ["Japanese", "Cocktails"],
      "price_level": "$$",
      "rating": 4.6,
      "match_highlight": "Why this spot matches the request.",
      "coordinates": {{"lat": 40.7264, "lng": -73.9818}},
      "links": {{
        "google_maps": "https://maps.google.com/?q=...",
        "reservation_url": "https://resy.com/... (or null)",
        "reservation_platform": "Resy | OpenTable | SevenRooms | null"
      }},
      "itinerary_context": {{
        "best_time_slot": "5:00 PM - 7:00 PM",
        "estimated_duration_min": 75
      }}
    }}
  ],
  "quick_filters": ["Open Happy Hours Now", "Show Only Saved Spots"]
}}

Return 2-5 spots. Use real, accurate coordinates for any fallback spot you add.
"""


def build_system_prompt(saved_places):
    compact = [
        {k: p[k] for k in ("id", "name", "neighborhood", "cuisine", "price_level",
                            "rating", "lat", "lng", "notes", "happy_hour_info")}
        for p in saved_places
    ]
    return SYSTEM_PROMPT_TEMPLATE.format(saved_places_json=json.dumps(compact, indent=2))


def extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    return json.loads(text)


def call_openrouter(user_query, system_prompt, history):
    from openai import OpenAI

    client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
    messages = [{"role": "system", "content": system_prompt}]
    for m in history[-6:]:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": user_query})

    resp = client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.4,
    )
    return extract_json(resp.choices[0].message.content)


def rule_based_match(user_query, saved_places):
    """Offline fallback: keyword match against the saved list, no LLM required."""
    query_lower = user_query.lower()
    keywords = re.findall(r"[a-z]+", query_lower)

    def score(place):
        haystack = " ".join([
            place["name"], place["neighborhood"], " ".join(place["cuisine"]),
            place.get("notes", ""), place.get("happy_hour_info", ""),
        ]).lower()
        return sum(1 for kw in keywords if len(kw) > 2 and kw in haystack)

    scored = sorted(saved_places, key=score, reverse=True)
    top = [p for p in scored if score(p) > 0][:5]
    fallback_triggered = len(top) < 2
    if fallback_triggered:
        top = scored[:3]

    spots = []
    for p in top:
        spots.append({
            "id": p["id"],
            "name": p["name"],
            "source": "saved",
            "is_bookmarked": p["id"] in st.session_state.bookmarks,
            "neighborhood": p["neighborhood"],
            "cuisine": p["cuisine"],
            "price_level": p["price_level"],
            "rating": p["rating"],
            "match_highlight": p.get("happy_hour_info") or p.get("notes", ""),
            "coordinates": {"lat": p["lat"], "lng": p["lng"]},
            "links": {
                "google_maps": p.get("google_url", ""),
                "reservation_url": None,
                "reservation_platform": None,
            },
            "itinerary_context": {
                "best_time_slot": "6:00 PM - 8:00 PM",
                "estimated_duration_min": 90,
            },
        })

    if fallback_triggered:
        summary = "Offline mode (no LLM key set): few keyword matches found, showing top saved spots."
    else:
        summary = f"Offline mode (no LLM key set): matched {len(spots)} spots from your saved list."

    return {
        "summary": summary,
        "fallback_triggered": fallback_triggered,
        "spots": spots,
        "quick_filters": ["Open Happy Hours Now", "Show Only Saved Spots"],
    }


def get_recommendations(user_query, saved_places, history):
    system_prompt = build_system_prompt(saved_places)
    if OPENROUTER_API_KEY:
        try:
            return call_openrouter(user_query, system_prompt, history)
        except Exception as exc:  # noqa: BLE001 - surface any provider error, then degrade gracefully
            st.warning(f"LLM call failed ({exc}); falling back to offline keyword matching.")
    return rule_based_match(user_query, saved_places)


# ---------------------------------------------------------------------------
# Card + map rendering
# ---------------------------------------------------------------------------

def render_spot_card(spot, idx):
    sid = spot.get("id", f"spot-{idx}")
    is_bookmarked = sid in st.session_state.bookmarks
    badge = "🔖 SAVED" if spot.get("source") == "saved" else "✨ CURATED PICK"
    key_base = f"{sid}-{idx}"

    with st.container(border=True):
        header_cols = st.columns([5, 2])
        with header_cols[0]:
            st.markdown(
                f"**{spot.get('name', 'Unknown')}**   ⭐ {spot.get('rating', '—')}"
                f"   {spot.get('price_level', '$')}"
                f"   📍 {spot.get('neighborhood', '—')}"
            )
        with header_cols[1]:
            st.markdown(f"<div style='text-align:right'>{badge}</div>", unsafe_allow_html=True)

        cuisine = ", ".join(spot.get("cuisine", []))
        if cuisine:
            st.caption(cuisine)

        highlight = spot.get("match_highlight")
        if highlight:
            st.markdown(f"💡 {highlight}")

        itin = spot.get("itinerary_context") or {}
        if itin.get("best_time_slot"):
            st.caption(f"Best time: {itin['best_time_slot']} · ~{itin.get('estimated_duration_min', '?')} min")

        toolbar = st.columns(4)

        with toolbar[0]:
            label = "★ Saved" if is_bookmarked else "☆ Bookmark"
            if st.button(label, key=f"bm-{key_base}"):
                if is_bookmarked:
                    st.session_state.bookmarks.pop(sid, None)
                else:
                    st.session_state.bookmarks[sid] = spot
                st.rerun()

        with toolbar[1]:
            links = spot.get("links") or {}
            maps_url = links.get("google_maps") or "https://maps.google.com"
            st.link_button("Google Maps", maps_url)

        with toolbar[2]:
            links = spot.get("links") or {}
            reservation_url = links.get("reservation_url")
            platform = links.get("reservation_platform")
            if reservation_url:
                st.link_button(f"Book ({platform or 'Reserve'})", reservation_url)
            else:
                st.caption("No reservation link")

        with toolbar[3]:
            already_in_itinerary = any(i.get("id") == sid for i in st.session_state.itinerary)
            if st.button(
                "✓ In itinerary" if already_in_itinerary else "+ Itinerary",
                key=f"itin-{key_base}",
                disabled=already_in_itinerary,
            ):
                st.session_state.itinerary.append(spot)
                st.rerun()


def build_map(spots, saved_places):
    if spots:
        coords = [s["coordinates"] for s in spots if s.get("coordinates") and s["coordinates"].get("lat") is not None]
        center = (
            (sum(c["lat"] for c in coords) / len(coords), sum(c["lng"] for c in coords) / len(coords))
            if coords else NYC_CENTER
        )
        zoom = 13
        display_spots = spots
    else:
        center = NYC_CENTER
        zoom = 12
        display_spots = [
            {
                "id": p["id"],
                "name": p["name"],
                "neighborhood": p["neighborhood"],
                "source": "saved",
                "match_highlight": p.get("notes", ""),
                "coordinates": {"lat": p["lat"], "lng": p["lng"]},
            }
            for p in saved_places
        ]

    fmap = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    )

    plotted = []
    for spot in display_spots:
        coords = spot.get("coordinates")
        if not coords or coords.get("lat") is None:
            continue
        source = spot.get("source", "saved")
        icon = folium.Icon(
            color="blue" if source == "saved" else "green",
            icon="cutlery" if source == "saved" else "star",
            prefix="fa",
        )
        popup_html = (
            f"<b>{spot.get('name')}</b><br>{spot.get('neighborhood', '')}<br>"
            f"{spot.get('match_highlight', '')}"
        )
        folium.Marker(
            location=(coords["lat"], coords["lng"]),
            tooltip=spot.get("name"),
            popup=folium.Popup(popup_html, max_width=250),
            icon=icon,
        ).add_to(fmap)
        plotted.append((coords["lat"], coords["lng"]))

    if len(plotted) > 1:
        fmap.fit_bounds(plotted, padding=(30, 30))

    return fmap


# ---------------------------------------------------------------------------
# Browse / search (full dataset, independent of the chat's LLM picks)
# ---------------------------------------------------------------------------

def place_to_spot(place):
    category = place.get("category", "Eats")
    return {
        "id": place["id"],
        "name": place["name"],
        "source": "saved",
        "is_bookmarked": place["id"] in st.session_state.get("bookmarks", {}),
        "category": category,
        "neighborhood": place.get("neighborhood", ""),
        "cuisine": place.get("cuisine", []),
        "price_level": place.get("price_level", "$"),
        "rating": place.get("rating"),
        "match_highlight": place.get("happy_hour_info") or place.get("notes", ""),
        "coordinates": {"lat": place.get("lat"), "lng": place.get("lng")},
        "links": {
            "google_maps": place.get("google_url", ""),
            "reservation_url": None,
            "reservation_platform": None,
        },
        "itinerary_context": {
            "best_time_slot": "9:00 AM - 11:00 AM" if category == "Cafe" else "6:00 PM - 8:00 PM",
            "estimated_duration_min": 45 if category == "Cafe" else 75,
        },
    }


def filter_places(places, query, category):
    query_lower = (query or "").strip().lower()

    def matches(p):
        if category != "All" and p.get("category") != category:
            return False
        if not query_lower:
            return True
        haystack = " ".join([p["name"], p.get("neighborhood", ""), " ".join(p.get("cuisine", []))]).lower()
        return query_lower in haystack

    return [p for p in places if matches(p)]


# ---------------------------------------------------------------------------
# Upload / import (session-scoped, no database - lives in st.session_state)
# ---------------------------------------------------------------------------

UPLOAD_CATEGORY = "Eats"  # uploaded lists don't carry the Bar/Cafe/Eats split our demo CSVs do


def _placeholder_price_and_rating(name):
    price_level = ["$", "$", "$$", "$$", "$$$"][int(enrich_places.deterministic_unit(name, "price") * 5)]
    rating = round(4.0 + enrich_places.deterministic_unit(name, "rating") * 0.8, 1)
    return price_level, rating


def parse_uploaded_csv(uploaded_file, progress_bar=None, status=None):
    """Parse a Google Maps list-export CSV (Title/URL columns), geocoding each
    row via free Nominatim (rate-limited) with a synthetic-coordinate fallback.
    Returns (places, skipped_count)."""
    raw_bytes = uploaded_file.getvalue()
    if not raw_bytes:
        raise ValueError("The uploaded file is empty.")
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Could not read this file as UTF-8 text.") from exc

    try:
        reader = csv.DictReader(io.StringIO(text))
        fieldnames = reader.fieldnames or []
    except csv.Error as exc:
        raise ValueError("Could not parse this as a CSV file.") from exc

    fieldmap = {(fn or "").strip().lower(): fn for fn in fieldnames}
    name_field = fieldmap.get("title") or fieldmap.get("name")
    if not name_field:
        raise ValueError("No 'Title' or 'name' column found — expected a Google Maps list export format.")
    url_field = fieldmap.get("url")

    rows = []
    for row in reader:
        name = (row.get(name_field) or "").strip()
        if not name:
            continue
        url = (row.get(url_field) or "").strip() if url_field else ""
        rows.append({"name": name, "url": url, "category": UPLOAD_CATEGORY})

    if not rows:
        raise ValueError("No places found in the uploaded CSV.")

    rows = enrich_places.dedupe(rows)
    enrich_places.assign_unique_ids(rows)

    session = requests.Session()
    n = len(rows)
    places = []
    for i, row in enumerate(rows):
        name = row["name"]
        if status is not None:
            status.text(f"Geocoding {i + 1}/{n}: {name}…")

        geo = enrich_places.nominatim_geocode(session, name)
        time.sleep(enrich_places.NOMINATIM_DELAY_SECONDS)
        if geo:
            lat, lng, neighborhood = geo["lat"], geo["lng"], geo.get("neighborhood")
            source = "nominatim"
        else:
            synth = enrich_places.synthetic_location(name)
            lat, lng, neighborhood = synth["lat"], synth["lng"], synth["neighborhood"]
            source = "offline_fallback"

        price_level, rating = _placeholder_price_and_rating(name)
        places.append({
            "id": row["id"],
            "name": name,
            "category": UPLOAD_CATEGORY,
            "neighborhood": neighborhood or "New York",
            "cuisine": enrich_places.classify_cuisine(name, UPLOAD_CATEGORY),
            "price_level": price_level,
            "rating": rating,
            "lat": round(float(lat), 4),
            "lng": round(float(lng), 4),
            "google_url": row.get("url", ""),
            "notes": "Imported from your uploaded CSV.",
            "happy_hour_info": "Not listed — check with the venue for current happy hour specials.",
            "_enrichment_source": source,
        })
        if progress_bar is not None:
            progress_bar.progress((i + 1) / n)

    return places, 0


def parse_uploaded_json(uploaded_file):
    """Parse a Google Takeout 'Saved Places.json' export (a GeoJSON
    FeatureCollection, coordinates as [lng, lat]) - already has real
    coordinates, so no geocoding needed. Returns (places, skipped_count)."""
    raw_bytes = uploaded_file.getvalue()
    if not raw_bytes:
        raise ValueError("The uploaded file is empty.")
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Could not parse this as a JSON file.") from exc

    if not isinstance(data, dict) or data.get("type") != "FeatureCollection" or not data.get("features"):
        raise ValueError(
            "This doesn't look like a Google Takeout 'Saved Places.json' export "
            "(expected a GeoJSON FeatureCollection)."
        )

    raw_entries = []
    skipped = 0
    for feature in data["features"]:
        try:
            lng, lat = feature["geometry"]["coordinates"]
            name = feature["properties"]["location"]["name"].strip()
            if not name:
                raise ValueError("blank name")
        except (KeyError, TypeError, ValueError):
            skipped += 1
            continue
        address = ((feature.get("properties") or {}).get("location") or {}).get("address", "")
        raw_entries.append({"name": name, "lat": lat, "lng": lng, "address": address})

    if not raw_entries:
        raise ValueError("No usable places found in this file (entries are missing name/coordinates).")

    enrich_places.assign_unique_ids(raw_entries)

    places = []
    for entry in raw_entries:
        name = entry["name"]
        price_level, rating = _placeholder_price_and_rating(name)
        places.append({
            "id": entry["id"],
            "name": name,
            "category": UPLOAD_CATEGORY,
            "neighborhood": entry.get("address") or "New York",
            "cuisine": enrich_places.classify_cuisine(name, UPLOAD_CATEGORY),
            "price_level": price_level,
            "rating": rating,
            "lat": round(float(entry["lat"]), 4),
            "lng": round(float(entry["lng"]), 4),
            "google_url": "",
            "notes": "Imported from your Google Takeout saved places.",
            "happy_hour_info": "Not listed — check with the venue for current happy hour specials.",
            "_enrichment_source": "takeout_json",
        })

    return places, skipped


def get_active_places():
    uploaded = st.session_state.get("uploaded_places")
    if uploaded:
        return uploaded
    return load_places(DATA_PATH.stat().st_mtime)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar():
    st.sidebar.title("🍽️ Your NYC Concierge")

    st.sidebar.subheader(f"Bookmarked ({len(st.session_state.bookmarks)})")
    if not st.session_state.bookmarks:
        st.sidebar.caption("No saved spots yet — bookmark a card to see it here.")
    else:
        for sid, spot in list(st.session_state.bookmarks.items()):
            cols = st.sidebar.columns([4, 1])
            cols[0].markdown(f"**{spot.get('name')}** · {spot.get('neighborhood', '')}")
            if cols[1].button("✕", key=f"unbm-{sid}"):
                st.session_state.bookmarks.pop(sid, None)
                st.rerun()

    st.sidebar.divider()
    st.sidebar.subheader(f"Itinerary ({len(st.session_state.itinerary)})")
    if not st.session_state.itinerary:
        st.sidebar.caption("No stops added yet — use “+ Itinerary” on a card.")
    else:
        for idx, spot in enumerate(st.session_state.itinerary):
            itin = spot.get("itinerary_context") or {}
            cols = st.sidebar.columns([4, 1])
            time_slot = itin.get("best_time_slot", "Time TBD")
            duration = itin.get("estimated_duration_min", "?")
            cols[0].markdown(f"**{idx + 1}. {spot.get('name')}**  \n{time_slot} · ~{duration} min")
            if cols[1].button("✕", key=f"unitin-{idx}"):
                st.session_state.itinerary.pop(idx)
                st.rerun()

    st.sidebar.divider()
    reset_cols = st.sidebar.columns(2)
    if reset_cols[0].button("Clear bookmarks"):
        st.session_state.bookmarks = {}
        st.rerun()
    if reset_cols[1].button("Clear itinerary"):
        st.session_state.itinerary = []
        st.rerun()
    if st.sidebar.button("Reset entire session", type="primary"):
        st.session_state.messages = []
        st.session_state.bookmarks = {}
        st.session_state.itinerary = []
        st.session_state.last_spots = []
        st.session_state.last_summary = ""
        st.session_state.last_filters = []
        st.session_state.browse_query = ""
        st.session_state.browse_category = "All"
        st.session_state.uploaded_places = None
        st.session_state.upload_status = None
        st.session_state._last_upload_sig = None
        st.rerun()

    if not OPENROUTER_API_KEY:
        st.sidebar.divider()
        st.sidebar.info(
            "No OPENROUTER_API_KEY set — running in offline keyword-matching mode. "
            "See .env.example."
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def process_query(query, saved_places):
    st.session_state.messages.append({"role": "user", "content": query})
    result = get_recommendations(query, saved_places, st.session_state.messages)

    for spot in result.get("spots", []):
        spot["is_bookmarked"] = spot.get("id") in st.session_state.bookmarks

    st.session_state.last_spots = result.get("spots", [])
    st.session_state.last_summary = result.get("summary", "")
    st.session_state.last_filters = result.get("quick_filters", [])

    st.session_state.messages.append({"role": "assistant", "content": result.get("summary", "")})


def render_mode_toggle():
    mode_cols = st.columns([1, 1, 0.7])
    if mode_cols[0].button(
        "💬 Concierge Chat", use_container_width=True,
        type="primary" if st.session_state.view_mode == "chat" else "secondary",
    ):
        st.session_state.view_mode = "chat"
        st.rerun()
    if mode_cols[1].button(
        "🔎 Browse All Spots", use_container_width=True,
        type="primary" if st.session_state.view_mode == "browse" else "secondary",
    ):
        st.session_state.view_mode = "browse"
        st.rerun()
    with mode_cols[2]:
        render_import_popover()


def render_import_popover():
    with st.popover("📤 Import", use_container_width=True):
        if st.session_state.uploaded_places:
            st.caption(f"Using {len(st.session_state.uploaded_places)} uploaded spots instead of the demo dataset.")
            if st.button("✕ Remove uploaded data (use demo dataset)", use_container_width=True):
                st.session_state.uploaded_places = None
                st.rerun()
            st.divider()

        uploaded_file = st.file_uploader(
            "Import your own places",
            type=["csv", "json"],
            help=(
                "CSV: a Google Maps list export (Title/URL columns) — geocoding takes "
                "~1 sec/row, so a large list can take a couple minutes. "
                "JSON: a Google Takeout 'Saved Places.json' export — imports instantly."
            ),
        )
        if uploaded_file is not None:
            file_sig = (uploaded_file.name, uploaded_file.size)
            if st.session_state._last_upload_sig != file_sig:
                st.session_state._last_upload_sig = file_sig
                try:
                    if uploaded_file.name.lower().endswith(".json"):
                        with st.spinner("Parsing…"):
                            places, skipped = parse_uploaded_json(uploaded_file)
                    else:
                        progress_bar = st.progress(0.0)
                        status = st.empty()
                        places, skipped = parse_uploaded_csv(uploaded_file, progress_bar, status)
                except ValueError as exc:
                    st.session_state.upload_status = ("error", f"Import failed: {exc}")
                else:
                    st.session_state.uploaded_places = places
                    msg = f"{len(places)} spots imported"
                    if skipped:
                        msg += f" ({skipped} entries skipped — missing name or coordinates)"
                    st.session_state.upload_status = ("success", msg)
                st.rerun()


def render_chat_view(saved_places):
    chat_box = st.container(height=380, border=True)
    with chat_box:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if st.session_state.last_filters:
        st.write("Quick filters:")
        filter_cols = st.columns(len(st.session_state.last_filters))
        for i, label in enumerate(st.session_state.last_filters):
            if filter_cols[i].button(label, key=f"qf-{i}"):
                st.session_state.pending_query = label
                st.rerun()

    query = st.chat_input("e.g. Asian happy hour in East Village for 6 people")
    if st.session_state.pending_query:
        query = st.session_state.pending_query
        st.session_state.pending_query = None

    if query:
        with st.spinner("Finding spots..."):
            process_query(query, saved_places)
        st.rerun()

    st.divider()
    st.subheader(f"Recommendations ({len(st.session_state.last_spots)})")
    if st.session_state.last_summary:
        st.info(st.session_state.last_summary)
    if not st.session_state.last_spots:
        st.caption("Ask a question above to get recommendations.")
    else:
        for idx, spot in enumerate(st.session_state.last_spots):
            render_spot_card(spot, idx)

    return st.session_state.last_spots


def render_browse_view(saved_places):
    st.text_input(
        "Search all spots",
        key="browse_query",
        placeholder="Search by name, neighborhood, or cuisine (e.g. tacos, East Village, bagels)",
    )

    chip_cols = st.columns(len(CATEGORY_CHIPS))
    for col, (label, value) in zip(chip_cols, CATEGORY_CHIPS):
        if col.button(
            label, key=f"chip-{value}", use_container_width=True,
            type="primary" if st.session_state.browse_category == value else "secondary",
        ):
            st.session_state.browse_category = value
            st.rerun()

    filtered = filter_places(saved_places, st.session_state.browse_query, st.session_state.browse_category)
    spots = [place_to_spot(p) for p in filtered]

    st.divider()
    st.subheader(f"Browse ({len(spots)} of {len(saved_places)})")
    if not spots:
        st.caption("No spots match your search — try a different keyword or category.")
    else:
        if len(spots) > BROWSE_CARD_LIMIT:
            st.caption(
                f"Showing the first {BROWSE_CARD_LIMIT} of {len(spots)} matches — "
                "the map on the right still plots all of them. Narrow your search to see more cards."
            )
        for idx, spot in enumerate(spots[:BROWSE_CARD_LIMIT]):
            render_spot_card(spot, idx)

    return spots


def main():
    saved_places = get_active_places()
    init_state(saved_places)

    st.title("🍽️ NYC Dining Concierge")
    if st.session_state.uploaded_places:
        st.caption(f"{len(saved_places)} spots from your uploaded list — chat for curated picks, or search and filter.")
    else:
        st.caption(
            f"{len(saved_places)} saved NYC spots — chat for curated picks, or search and filter the full list."
        )

    render_sidebar()

    left, right = st.columns([1, 1], gap="large")

    with left:
        render_mode_toggle()
        if st.session_state.upload_status:
            kind, msg = st.session_state.upload_status
            (st.success if kind == "success" else st.error)(msg)
            st.session_state.upload_status = None
        st.divider()
        if st.session_state.view_mode == "browse":
            map_spots = render_browse_view(saved_places)
        else:
            map_spots = render_chat_view(saved_places)

    with right:
        st.subheader("Map")
        fmap = build_map(map_spots, saved_places)
        st_folium(fmap, height=560, use_container_width=True, key="dining_map")
        st.caption("🔵 Blue = your saved spots · 🟢 Green = curated fallback picks")


if __name__ == "__main__":
    main()
