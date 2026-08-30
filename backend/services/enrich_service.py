"""Ported 1:1 from the original repo's enrich_places.py - the parts the
Streamlit app's CSV/JSON upload feature actually calls at runtime (not the
CLI entrypoint). Same logic, same constants, same behavior."""

from __future__ import annotations

import hashlib
import re
import sys

import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_USER_AGENT = "NYCDiningConcierge/1.0 (personal project, contact via GitHub)"
NOMINATIM_DELAY_SECONDS = 1.1  # respect Nominatim's 1 req/sec usage policy
NYC_VIEWBOX = "-74.26,40.917,-73.70,40.49"  # left,top,right,bottom

NYC_LAT_RANGE = (40.680, 40.780)
NYC_LNG_RANGE = (-74.010, -73.930)

FALLBACK_NEIGHBORHOODS = [
    "East Village", "West Village", "Lower East Side", "Williamsburg",
    "Chinatown", "Chelsea", "SoHo", "NoHo", "Nolita", "Flatiron",
    "Greenpoint", "Bushwick", "Bedford-Stuyvesant", "Astoria",
]

CATEGORY_DEFAULT_TAG = {"Bar": "Bar", "Cafe": "Cafe", "Eats": "Restaurant"}

KEYWORD_TAGS = [
    ("taqueria", ["Mexican", "Tacos"]), ("taco", ["Mexican", "Tacos"]), ("burrito", ["Mexican"]),
    ("pizzeria", ["Pizza", "Italian"]), ("pizza", ["Pizza", "Italian"]),
    ("sushi", ["Japanese", "Sushi"]), ("ramen", ["Japanese", "Ramen"]), ("izakaya", ["Japanese"]),
    ("dumpling", ["Chinese", "Dumplings"]), ("dim sum", ["Chinese", "Dim Sum"]),
    ("matcha", ["Matcha", "Tea"]), ("bagel", ["Bagels"]), ("bakery", ["Bakery"]), ("bake", ["Bakery"]),
    ("cheesecake", ["Dessert", "Bakery"]), ("ice cream", ["Dessert"]), ("gelato", ["Dessert", "Italian"]),
    ("candy", ["Dessert"]), ("halal", ["Halal", "Middle Eastern"]), ("shawarma", ["Middle Eastern"]),
    ("falafel", ["Middle Eastern"]), ("za'atar", ["Middle Eastern"]), ("wine", ["Wine Bar"]),
    ("cocktail", ["Cocktail Bar"]), ("speakeasy", ["Cocktail Bar"]), ("pub", ["Pub", "Beer"]),
    ("grill", ["American"]), ("jazz", ["Jazz Bar", "Live Music"]), ("rooftop", ["Rooftop"]),
    ("korean", ["Korean"]), ("thai", ["Thai"]), ("indian", ["Indian"]), ("chaap", ["Indian"]),
    ("punjabi", ["Indian"]), ("dosa", ["Indian"]), ("chinese", ["Chinese"]), ("cantonese", ["Chinese"]),
    ("sichuan", ["Chinese", "Sichuan"]), ("mexican", ["Mexican"]), ("vietnamese", ["Vietnamese"]),
    ("banh mi", ["Vietnamese"]), ("pho", ["Vietnamese"]), ("deli", ["Deli"]), ("pasta", ["Italian"]),
    ("italian", ["Italian"]), ("trattoria", ["Italian"]), ("french", ["French"]), ("bistro", ["French"]),
    ("japanese", ["Japanese"]), ("coffee", ["Coffee"]), ("café", ["Cafe"]), ("cafe", ["Cafe"]),
    ("tea", ["Tea"]), ("bar", ["Bar"]),
]


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or hashlib.md5(name.encode()).hexdigest()[:8]


def classify_cuisine(name: str, category: str) -> list[str]:
    name_lower = name.lower()
    tags: list[str] = []
    for keyword, kw_tags in KEYWORD_TAGS:
        if keyword in name_lower:
            for t in kw_tags:
                if t not in tags:
                    tags.append(t)
        if len(tags) >= 3:
            break
    if not tags:
        tags = [CATEGORY_DEFAULT_TAG.get(category, "Restaurant")]
    return tags


def dedupe(entries: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for entry in entries:
        key = (entry["name"].strip().lower(), entry.get("url", "").strip())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped


def assign_unique_ids(entries: list[dict]) -> None:
    counts: dict[str, int] = {}
    for entry in entries:
        base = slugify(entry["name"])
        counts[base] = counts.get(base, 0) + 1
        entry["id"] = base if counts[base] == 1 else f"{base}-{counts[base]}"


def deterministic_unit(seed: str, salt: str) -> float:
    digest = hashlib.md5(f"{seed}:{salt}".encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def synthetic_location(name: str) -> dict:
    lat = NYC_LAT_RANGE[0] + deterministic_unit(name, "lat") * (NYC_LAT_RANGE[1] - NYC_LAT_RANGE[0])
    lng = NYC_LNG_RANGE[0] + deterministic_unit(name, "lng") * (NYC_LNG_RANGE[1] - NYC_LNG_RANGE[0])
    neighborhood = FALLBACK_NEIGHBORHOODS[int(deterministic_unit(name, "hood") * len(FALLBACK_NEIGHBORHOODS))]
    return {"lat": round(lat, 4), "lng": round(lng, 4), "neighborhood": neighborhood}


def nominatim_geocode(session: requests.Session, name: str) -> dict | None:
    try:
        resp = session.get(
            NOMINATIM_URL,
            params={
                "q": f"{name}, New York, NY", "format": "jsonv2", "addressdetails": 1,
                "limit": 1, "countrycodes": "us", "viewbox": NYC_VIEWBOX, "bounded": 1,
            },
            headers={"User-Agent": NOMINATIM_USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        if not results:
            return None
        result = results[0]
        address = result.get("address", {})
        neighborhood = (
            address.get("neighbourhood") or address.get("suburb")
            or address.get("quarter") or address.get("city_district")
        )
        return {"lat": float(result["lat"]), "lng": float(result["lon"]), "neighborhood": neighborhood}
    except (requests.RequestException, KeyError, ValueError, IndexError) as exc:
        print(f"  Nominatim lookup failed for '{name}': {exc}", file=sys.stderr)
        return None


def placeholder_price_and_rating(name: str) -> tuple[str, float]:
    price_level = ["$", "$", "$$", "$$", "$$$"][int(deterministic_unit(name, "price") * 5)]
    rating = round(4.0 + deterministic_unit(name, "rating") * 0.8, 1)
    return price_level, rating
