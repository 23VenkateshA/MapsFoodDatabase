"""Free, no-API-key geo helpers: Nominatim geocoding (same service/pattern
already used by enrich_service.py for the CSV import path, just resolving a
single free-text address instead of a place name) plus a straight-line-
distance walk-time estimate for radius search and itinerary travel time.
No paid routing API (e.g. OSRM) is used - see backend/README.md for the
accuracy tradeoff this implies."""

from __future__ import annotations

import math

import requests

from .enrich_service import NOMINATIM_URL, NOMINATIM_USER_AGENT, NYC_VIEWBOX

WALK_SPEED_MPH = 3.0
EARTH_RADIUS_MILES = 3958.8


def geocode_address(address: str) -> tuple[float, float] | None:
    resp = requests.get(
        NOMINATIM_URL,
        params={
            "q": address,
            "format": "jsonv2",
            "limit": 1,
            "countrycodes": "us",
            "viewbox": NYC_VIEWBOX,
            "bounded": 1,
        },
        headers={"User-Agent": NOMINATIM_USER_AGENT},
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        return None
    return float(results[0]["lat"]), float(results[0]["lon"])


def haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


def walk_minutes(miles: float) -> int:
    return max(1, round((miles / WALK_SPEED_MPH) * 60))
