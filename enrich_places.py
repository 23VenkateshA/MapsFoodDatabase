"""
Data enrichment utility for NYC Dining Concierge.

Takes one or more plain CSV exports of place names + Google Maps URLs
(e.g. a Google Maps "saved places" list export) and produces a places.json
file matching the app's schema (id, name, category, neighborhood, cuisine,
price_level, rating, lat, lng, google_url, notes, happy_hour_info).

Enrichment tiers, tried in order per place:
  1. Google Places API, if GOOGLE_PLACES_API_KEY is set - real coordinates,
     rating, price level, and formatted address.
  2. Free OpenStreetMap Nominatim geocoding (no key required) - real
     coordinates and address-derived neighborhood; rating/price/cuisine are
     still estimated, since Nominatim doesn't carry that data.
  3. Fully offline synthetic fallback - deterministic, reasonable
     placeholder metadata so the pipeline still works with no network.

Usage (single file):
    python enrich_places.py --input raw_places.csv --output data/places.json

Usage (multiple category-tagged files, e.g. this project's Google Maps
list exports):
    python enrich_places.py \\
        --input "Bar:NYC Bars.csv" \\
        --input "Cafe:NYC Cafe.csv" \\
        --input "Eats:NYC Eats.csv" \\
        --output data/places.json

Input CSV format: a header row containing at least a "Title" (or "name")
column and a "URL" column - this matches Google Maps' list-export format
(Title,Note,URL,Tags,Comment) as well as a simple name,url CSV.

Input JSON format:
    [{"name": "Some Restaurant", "url": "https://someresturant.com"}, ...]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_USER_AGENT = "NYCDiningConcierge/1.0 (personal project, contact via GitHub)"
NOMINATIM_DELAY_SECONDS = 1.1  # respect Nominatim's 1 req/sec usage policy
# Roughly the five boroughs, used to bound Nominatim search results.
NYC_VIEWBOX = "-74.26,40.917,-73.70,40.49"  # left,top,right,bottom

# Rough NYC bounding box used to generate plausible fallback coordinates.
NYC_LAT_RANGE = (40.680, 40.780)
NYC_LNG_RANGE = (-74.010, -73.930)

FALLBACK_NEIGHBORHOODS = [
    "East Village", "West Village", "Lower East Side", "Williamsburg",
    "Chinatown", "Chelsea", "SoHo", "NoHo", "Nolita", "Flatiron",
    "Greenpoint", "Bushwick", "Bedford-Stuyvesant", "Astoria",
]

CATEGORY_DEFAULT_TAG = {
    "Bar": "Bar",
    "Cafe": "Cafe",
    "Eats": "Restaurant",
}

CATEGORY_HAPPY_HOUR = {
    "Bar": "Not listed — check with the venue for current happy hour specials.",
    "Cafe": "N/A — coffee/bakery spot.",
    "Eats": "Not listed — check with the venue for current happy hour specials.",
}

# Ordered (keyword, tags) pairs used to guess cuisine/type from a place name.
# Checked in order; first few matches are kept. This is a heuristic label,
# not a verified fact.
KEYWORD_TAGS = [
    ("taqueria", ["Mexican", "Tacos"]),
    ("taco", ["Mexican", "Tacos"]),
    ("burrito", ["Mexican"]),
    ("pizzeria", ["Pizza", "Italian"]),
    ("pizza", ["Pizza", "Italian"]),
    ("sushi", ["Japanese", "Sushi"]),
    ("ramen", ["Japanese", "Ramen"]),
    ("izakaya", ["Japanese"]),
    ("dumpling", ["Chinese", "Dumplings"]),
    ("dim sum", ["Chinese", "Dim Sum"]),
    ("matcha", ["Matcha", "Tea"]),
    ("bagel", ["Bagels"]),
    ("bakery", ["Bakery"]),
    ("bake", ["Bakery"]),
    ("cheesecake", ["Dessert", "Bakery"]),
    ("ice cream", ["Dessert"]),
    ("gelato", ["Dessert", "Italian"]),
    ("candy", ["Dessert"]),
    ("halal", ["Halal", "Middle Eastern"]),
    ("shawarma", ["Middle Eastern"]),
    ("falafel", ["Middle Eastern"]),
    ("za'atar", ["Middle Eastern"]),
    ("wine", ["Wine Bar"]),
    ("cocktail", ["Cocktail Bar"]),
    ("speakeasy", ["Cocktail Bar"]),
    ("pub", ["Pub", "Beer"]),
    ("grill", ["American"]),
    ("jazz", ["Jazz Bar", "Live Music"]),
    ("rooftop", ["Rooftop"]),
    ("korean", ["Korean"]),
    ("thai", ["Thai"]),
    ("indian", ["Indian"]),
    ("chaap", ["Indian"]),
    ("punjabi", ["Indian"]),
    ("dosa", ["Indian"]),
    ("chinese", ["Chinese"]),
    ("cantonese", ["Chinese"]),
    ("sichuan", ["Chinese", "Sichuan"]),
    ("mexican", ["Mexican"]),
    ("vietnamese", ["Vietnamese"]),
    ("banh mi", ["Vietnamese"]),
    ("pho", ["Vietnamese"]),
    ("deli", ["Deli"]),
    ("pasta", ["Italian"]),
    ("italian", ["Italian"]),
    ("trattoria", ["Italian"]),
    ("french", ["French"]),
    ("bistro", ["French"]),
    ("japanese", ["Japanese"]),
    ("coffee", ["Coffee"]),
    ("café", ["Cafe"]),
    ("cafe", ["Cafe"]),
    ("tea", ["Tea"]),
    ("bar", ["Bar"]),
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


def parse_csv_rows(path: Path, category: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldmap = {(fn or "").strip().lower(): fn for fn in (reader.fieldnames or [])}
        name_field = fieldmap.get("title") or fieldmap.get("name")
        url_field = fieldmap.get("url")
        if not name_field:
            raise ValueError(f"Could not find a Title/name column in {path}")

        rows = []
        for row in reader:
            name = (row.get(name_field) or "").strip()
            if not name:
                continue
            url = (row.get(url_field) or "").strip() if url_field else ""
            rows.append({"name": name, "url": url, "category": category})
        return rows


def parse_json_rows(path: Path, category: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return [
        {"name": item["name"].strip(), "url": (item.get("url") or "").strip(), "category": category}
        for item in raw if item.get("name")
    ]


def infer_category(path: Path) -> str:
    stem_lower = path.stem.lower()
    if "bar" in stem_lower:
        return "Bar"
    if "cafe" in stem_lower or "caf\u00e9" in stem_lower:
        return "Cafe"
    return "Eats"


def load_input_spec(spec: str) -> list[dict]:
    """Parse a single --input value, which may be "Category:path" or just "path"."""
    if ":" in spec and not spec[1:3] == ":\\":  # avoid mangling e.g. C:\path on Windows
        category, _, raw_path = spec.partition(":")
        category = category.strip() or None
        path = Path(raw_path.strip())
    else:
        category = None
        path = Path(spec)

    if not path.exists():
        print(f"Input file not found: {path}", file=sys.stderr)
        sys.exit(1)

    if category is None:
        category = infer_category(path)

    if path.suffix.lower() == ".csv":
        return parse_csv_rows(path, category)
    if path.suffix.lower() == ".json":
        return parse_json_rows(path, category)
    raise ValueError(f"Unsupported input file type: {path.suffix}")


def dedupe(entries: list[dict]) -> list[dict]:
    """Drop exact (name, url) duplicates; keep same-name/different-url entries
    (distinct physical locations) as separate records."""
    seen = set()
    deduped = []
    for entry in entries:
        key = (entry["name"].strip().lower(), entry["url"].strip())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped


def assign_unique_ids(entries: list[dict]) -> None:
    """Mutates entries in place, adding a unique 'id' slug, suffixing
    duplicates that share a base name (different branches of the same
    place) with -2, -3, etc."""
    counts: dict[str, int] = {}
    for entry in entries:
        base = slugify(entry["name"])
        counts[base] = counts.get(base, 0) + 1
        entry["id"] = base if counts[base] == 1 else f"{base}-{counts[base]}"


def deterministic_unit(seed: str, salt: str) -> float:
    """Deterministic pseudo-random float in [0, 1) derived from a name + salt."""
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
                "q": f"{name}, New York, NY",
                "format": "jsonv2",
                "addressdetails": 1,
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
        result = results[0]
        address = result.get("address", {})
        neighborhood = (
            address.get("neighbourhood") or address.get("suburb")
            or address.get("quarter") or address.get("city_district")
        )
        return {
            "lat": float(result["lat"]),
            "lng": float(result["lon"]),
            "neighborhood": neighborhood,
            "display_name": result.get("display_name"),
        }
    except (requests.RequestException, KeyError, ValueError, IndexError) as exc:
        print(f"  Nominatim lookup failed for '{name}': {exc}", file=sys.stderr)
        return None


def google_places_metadata(name: str) -> dict | None:
    if not GOOGLE_PLACES_API_KEY:
        return None
    try:
        find_resp = requests.get(
            "https://maps.googleapis.com/maps/api/place/findplacefromtext/json",
            params={
                "input": f"{name} New York City",
                "inputtype": "textquery",
                "fields": "place_id",
                "key": GOOGLE_PLACES_API_KEY,
            },
            timeout=10,
        )
        find_resp.raise_for_status()
        candidates = find_resp.json().get("candidates", [])
        if not candidates:
            return None
        place_id = candidates[0]["place_id"]

        details_resp = requests.get(
            "https://maps.googleapis.com/maps/api/place/details/json",
            params={
                "place_id": place_id,
                "fields": "name,geometry,rating,price_level,formatted_address,url",
                "key": GOOGLE_PLACES_API_KEY,
            },
            timeout=10,
        )
        details_resp.raise_for_status()
        result = details_resp.json().get("result", {})
        if not result:
            return None

        location = result.get("geometry", {}).get("location", {})
        price_map = {0: "$", 1: "$", 2: "$$", 3: "$$$", 4: "$$$$"}
        formatted_address = result.get("formatted_address", "")
        return {
            "neighborhood": formatted_address.split(",")[1].strip() if "," in formatted_address else "New York",
            "price_level": price_map.get(result.get("price_level"), "$$"),
            "rating": result.get("rating"),
            "lat": location.get("lat"),
            "lng": location.get("lng"),
            "google_url": result.get("url"),
            "_source": "google_places",
        }
    except (requests.RequestException, KeyError, IndexError) as exc:
        print(f"  Google Places lookup failed for '{name}': {exc}", file=sys.stderr)
        return None


def enrich(entries: list[dict]) -> list[dict]:
    places = []
    session = requests.Session()
    use_nominatim = not GOOGLE_PLACES_API_KEY

    for i, entry in enumerate(entries):
        name = entry["name"]
        category = entry["category"]
        print(f"[{i + 1}/{len(entries)}] Enriching: {name} ({category})")

        meta = google_places_metadata(name)
        source = "google_places" if meta else None

        if meta is None and use_nominatim:
            geo = nominatim_geocode(session, name)
            time.sleep(NOMINATIM_DELAY_SECONDS)
            if geo:
                meta = {"lat": geo["lat"], "lng": geo["lng"], "neighborhood": geo.get("neighborhood")}
                source = "nominatim"

        synth = synthetic_location(name)
        lat = (meta or {}).get("lat") or synth["lat"]
        lng = (meta or {}).get("lng") or synth["lng"]
        neighborhood = (meta or {}).get("neighborhood") or synth["neighborhood"]
        price_level = (meta or {}).get("price_level") or ["$", "$", "$$", "$$", "$$$"][
            int(deterministic_unit(name, "price") * 5)
        ]
        rating = (meta or {}).get("rating") or round(4.0 + deterministic_unit(name, "rating") * 0.8, 1)
        source = source or "offline_fallback"

        places.append({
            "id": entry["id"],
            "name": name,
            "category": category,
            "neighborhood": neighborhood,
            "cuisine": classify_cuisine(name, category),
            "price_level": price_level,
            "rating": round(float(rating), 1),
            "lat": round(float(lat), 4),
            "lng": round(float(lng), 4),
            "google_url": entry.get("url") or (meta or {}).get("google_url") or "",
            "notes": f"Imported from your NYC {category} list.",
            "happy_hour_info": CATEGORY_HAPPY_HOUR.get(category, "Not listed."),
            "_enrichment_source": source,
        })
    return places


def main():
    parser = argparse.ArgumentParser(description="Enrich place names/URLs into places.json")
    parser.add_argument(
        "--input", "-i", action="append", required=True,
        help='Path to input CSV/JSON, optionally prefixed "Category:" (e.g. "Bar:NYC Bars.csv"). '
             "Repeatable.",
    )
    parser.add_argument("--output", "-o", default="data/places.json", help="Path to write enriched JSON")
    args = parser.parse_args()

    entries: list[dict] = []
    for spec in args.input:
        entries.extend(load_input_spec(spec))

    if not entries:
        print("No entries found in input file(s).", file=sys.stderr)
        sys.exit(1)

    entries = dedupe(entries)
    assign_unique_ids(entries)

    if not GOOGLE_PLACES_API_KEY:
        print(
            "GOOGLE_PLACES_API_KEY not set — using free Nominatim geocoding where possible, "
            "with synthetic fallback for anything it can't find.\n"
        )

    enriched = enrich(entries)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=2)

    print(f"\nWrote {len(enriched)} places to {output_path}")


if __name__ == "__main__":
    main()
