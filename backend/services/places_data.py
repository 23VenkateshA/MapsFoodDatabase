"""Ported from load_places()/get_active_places() in the original app.py.
Same static JSON file, no database migration - the file is small (158
records) and reads are cheap, so it's cached in memory at import time
rather than re-read per request."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "places.json"

# Generic filler enrich_places.py / import_service.py write into
# happy_hour_info when no real happy-hour info was found - not something a
# user wants to read as if it were an actual detail about the place.
NO_INFO_HAPPY_HOUR = {
    "Not listed — check with the venue for current happy hour specials.",
    "N/A — coffee/bakery spot.",
}


def _real_happy_hour(info: str | None) -> str:
    return info if info and info not in NO_INFO_HAPPY_HOUR else ""


@lru_cache(maxsize=1)
def load_demo_places() -> list[dict]:
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def filter_places(places: list[dict], query: str | None, category: str | None) -> list[dict]:
    """Ported 1:1 from filter_places() in app.py."""
    query_lower = (query or "").strip().lower()
    category = category or "All"

    def matches(p: dict) -> bool:
        if category != "All" and p.get("category") != category:
            return False
        if not query_lower:
            return True
        haystack = " ".join([p["name"], p.get("neighborhood", ""), " ".join(p.get("cuisine", []))]).lower()
        return query_lower in haystack

    return [p for p in places if matches(p)]


def place_to_spot(place: dict, bookmarked_ids: set[str]) -> dict:
    """Ported 1:1 from place_to_spot() in app.py, including the Cafe vs.
    everything-else itinerary-context split. Per explicit instruction, the
    75-vs-90-minute inconsistency against the offline chat path has been
    aligned to 75 (this function's value) rather than ported as a bug."""
    category = place.get("category", "Eats")
    return {
        "id": place["id"],
        "name": place["name"],
        "source": "saved",
        "is_bookmarked": place["id"] in bookmarked_ids,
        "category": category,
        "neighborhood": place.get("neighborhood", ""),
        "cuisine": place.get("cuisine", []),
        "price_level": place.get("price_level", "$"),
        "rating": place.get("rating"),
        "match_highlight": _real_happy_hour(place.get("happy_hour_info")) or place.get("notes", ""),
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
