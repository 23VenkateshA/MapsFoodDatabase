"""Session-scoped persistence for bookmarks/itinerary/imported-dataset.

This is new: the original Streamlit app had zero persistence (st.session_state
lives only in server memory for the life of one browser tab's WebSocket
connection). A stateless REST API needs *some* place to keep this, so this
uses a lightweight SQLite store keyed by a session_id cookie the frontend
never has to know about - each browser gets its own isolated bookmarks/
itinerary/uploaded-dataset, closely mirroring the original per-tab isolation,
but now surviving backend restarts and multiple requests.

The demo auto-seed (4 bookmark ids + 1 itinerary id on a genuinely fresh
session) is preserved exactly: it fires once per session_id, tracked via the
`sessions` table's `initialized` flag, not by checking if bookmarks/itinerary
are empty - so Clear/Reset never re-triggers it, matching the original
st.session_state `if key not in st.session_state` semantics.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from .places_data import load_demo_places, place_to_spot

DATABASE_PATH = Path(os.getenv("DATABASE_PATH", Path(__file__).resolve().parent.parent / "data" / "app.db"))

SEED_BOOKMARK_IDS = ["212-east", "wiggle-room", "the-bean", "mahmoud-s-corner-halal-food-cart"]
SEED_ITINERARY_ID = "cello-s-pizzeria"


def _connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS sessions (session_id TEXT PRIMARY KEY, initialized INTEGER)")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS bookmarks (session_id TEXT, spot_id TEXT, spot_json TEXT, "
            "PRIMARY KEY (session_id, spot_id))"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS itinerary (session_id TEXT, spot_id TEXT, position INTEGER, spot_json TEXT, "
            "PRIMARY KEY (session_id, spot_id))"
        )
        conn.execute("CREATE TABLE IF NOT EXISTS uploaded_dataset (session_id TEXT PRIMARY KEY, places_json TEXT)")


def ensure_session_seeded(session_id: str) -> None:
    """Mirrors init_state()'s one-time seed - fires only for a session_id
    that has never been seen before, never again after that (even once
    Clear/Reset has emptied the tables)."""
    with _connect() as conn:
        row = conn.execute("SELECT initialized FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if row is not None:
            return  # already initialized (whether or not it's since been cleared)

        demo_places = load_demo_places()
        by_id = {p["id"]: p for p in demo_places}

        for i, spot_id in enumerate(SEED_BOOKMARK_IDS):
            place = by_id.get(spot_id)
            if not place:
                continue
            spot = place_to_spot(place, bookmarked_ids=set())
            conn.execute(
                "INSERT OR IGNORE INTO bookmarks (session_id, spot_id, spot_json) VALUES (?, ?, ?)",
                (session_id, spot_id, json.dumps(spot)),
            )

        seed_place = by_id.get(SEED_ITINERARY_ID)
        if seed_place:
            spot = place_to_spot(seed_place, bookmarked_ids=set())
            conn.execute(
                "INSERT OR IGNORE INTO itinerary (session_id, spot_id, position, spot_json) VALUES (?, ?, ?, ?)",
                (session_id, SEED_ITINERARY_ID, 0, json.dumps(spot)),
            )

        conn.execute("INSERT INTO sessions (session_id, initialized) VALUES (?, 1)", (session_id,))


def get_bookmarks(session_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("SELECT spot_json FROM bookmarks WHERE session_id = ?", (session_id,)).fetchall()
    return [json.loads(r["spot_json"]) for r in rows]


def get_bookmark_ids(session_id: str) -> set[str]:
    with _connect() as conn:
        rows = conn.execute("SELECT spot_id FROM bookmarks WHERE session_id = ?", (session_id,)).fetchall()
    return {r["spot_id"] for r in rows}


def add_bookmark(session_id: str, spot: dict) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO bookmarks (session_id, spot_id, spot_json) VALUES (?, ?, ?)",
            (session_id, spot["id"], json.dumps(spot)),
        )


def remove_bookmark(session_id: str, spot_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM bookmarks WHERE session_id = ? AND spot_id = ?", (session_id, spot_id))


def clear_bookmarks(session_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM bookmarks WHERE session_id = ?", (session_id,))


def get_itinerary(session_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT spot_json FROM itinerary WHERE session_id = ? ORDER BY position ASC", (session_id,)
        ).fetchall()
    return [json.loads(r["spot_json"]) for r in rows]


def add_itinerary_stop(session_id: str, spot: dict) -> None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS next_pos FROM itinerary WHERE session_id = ?", (session_id,)
        ).fetchone()
        conn.execute(
            "INSERT OR REPLACE INTO itinerary (session_id, spot_id, position, spot_json) VALUES (?, ?, ?, ?)",
            (session_id, spot["id"], row["next_pos"], json.dumps(spot)),
        )


def remove_itinerary_stop(session_id: str, spot_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM itinerary WHERE session_id = ? AND spot_id = ?", (session_id, spot_id))


def clear_itinerary(session_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM itinerary WHERE session_id = ?", (session_id,))


def get_uploaded_places(session_id: str) -> list[dict] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT places_json FROM uploaded_dataset WHERE session_id = ?", (session_id,)
        ).fetchone()
    return json.loads(row["places_json"]) if row else None


def set_uploaded_places(session_id: str, places: list[dict]) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO uploaded_dataset (session_id, places_json) VALUES (?, ?)",
            (session_id, json.dumps(places)),
        )


def clear_uploaded_places(session_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM uploaded_dataset WHERE session_id = ?", (session_id,))


def get_active_places(session_id: str) -> list[dict]:
    """Mirrors get_active_places() in app.py: uploaded dataset takes over
    entirely when present, otherwise the demo dataset."""
    uploaded = get_uploaded_places(session_id)
    return uploaded if uploaded else load_demo_places()


def reset_session(session_id: str) -> None:
    """Mirrors the "Reset entire session" button: clears bookmarks,
    itinerary, and the uploaded dataset. Does NOT re-seed - matches the
    original, which only seeds a session_state key that doesn't exist yet."""
    clear_bookmarks(session_id)
    clear_itinerary(session_id)
    clear_uploaded_places(session_id)
