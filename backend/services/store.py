"""Session-scoped persistence for bookmarks/itinerary/imported-dataset.

This is new: the original Streamlit app had zero persistence (st.session_state
lives only in server memory for the life of one browser tab's WebSocket
connection). A stateless REST API needs *some* place to keep this, so this
uses a lightweight SQLite store keyed by a session_id cookie the frontend
never has to know about - each browser gets its own isolated bookmarks/
itinerary/uploaded-dataset, closely mirroring the original per-tab isolation,
but now surviving backend restarts and multiple requests.

A session starts genuinely empty (no auto-seeded demo bookmarks/itinerary,
per explicit instruction) - `ensure_session_seeded` only records that a
session_id has been seen before, via the `sessions` table's `initialized`
flag, so a first-time visit and a page reload behave identically.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from .places_data import load_demo_places

DATABASE_PATH = Path(os.getenv("DATABASE_PATH", Path(__file__).resolve().parent.parent / "data" / "app.db"))


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
        conn.execute(
            "CREATE TABLE IF NOT EXISTS addresses (session_id TEXT, address_id TEXT, label TEXT, address TEXT, "
            "lat REAL, lng REAL, is_default INTEGER DEFAULT 0, PRIMARY KEY (session_id, address_id))"
        )


def ensure_session_seeded(session_id: str) -> None:
    """Records that a session_id has been seen before - a fresh session
    starts with empty bookmarks/itinerary, same as Clear/Reset leaves it."""
    with _connect() as conn:
        row = conn.execute("SELECT initialized FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if row is not None:
            return
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


def _address_row(row: sqlite3.Row) -> dict:
    return {
        "id": row["address_id"],
        "label": row["label"],
        "address": row["address"],
        "lat": row["lat"],
        "lng": row["lng"],
        "is_default": bool(row["is_default"]),
    }


def get_addresses(session_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT address_id, label, address, lat, lng, is_default FROM addresses "
            "WHERE session_id = ? ORDER BY is_default DESC, rowid ASC",
            (session_id,),
        ).fetchall()
    return [_address_row(r) for r in rows]


def get_address(session_id: str, address_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT address_id, label, address, lat, lng, is_default FROM addresses "
            "WHERE session_id = ? AND address_id = ?",
            (session_id, address_id),
        ).fetchone()
    return _address_row(row) if row else None


def add_address(session_id: str, address_id: str, label: str, raw_address: str, lat: float, lng: float) -> None:
    with _connect() as conn:
        is_first = (
            conn.execute("SELECT COUNT(*) AS n FROM addresses WHERE session_id = ?", (session_id,)).fetchone()["n"]
            == 0
        )
        conn.execute(
            "INSERT INTO addresses (session_id, address_id, label, address, lat, lng, is_default) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session_id, address_id, label, raw_address, lat, lng, 1 if is_first else 0),
        )


def delete_address(session_id: str, address_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM addresses WHERE session_id = ? AND address_id = ?", (session_id, address_id))


def set_default_address(session_id: str, address_id: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE addresses SET is_default = 0 WHERE session_id = ?", (session_id,))
        conn.execute(
            "UPDATE addresses SET is_default = 1 WHERE session_id = ? AND address_id = ?", (session_id, address_id)
        )


def reset_session(session_id: str) -> None:
    """Mirrors the "Reset entire session" button: clears bookmarks,
    itinerary, and the uploaded dataset. Does NOT re-seed - matches the
    original, which only seeds a session_state key that doesn't exist yet."""
    clear_bookmarks(session_id)
    clear_itinerary(session_id)
    clear_uploaded_places(session_id)
