"""
Data enrichment utility for NYC Dining Concierge.

Takes a plain list of place names (and optionally URLs) from a CSV or JSON
file and produces a places.json file matching the app's schema
(id, name, neighborhood, cuisine, price_level, rating, lat, lng, google_url,
notes, happy_hour_info).

If GOOGLE_PLACES_API_KEY is set, real coordinates/ratings/price levels/
addresses are fetched from the Google Places API. Otherwise, the script
generates deterministic, reasonable fallback metadata so the pipeline still
works completely offline.

Usage:
    python enrich_places.py --input raw_places.csv --output data/places.json
    python enrich_places.py --input raw_places.json --output data/places.json

Input CSV format (header row required):
    name,url
    Some Restaurant,https://someresturant.com

Input JSON format:
    [{"name": "Some Restaurant", "url": "https://someresturant.com"}, ...]
"""

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

# Rough NYC bounding box used to generate plausible fallback coordinates.
NYC_LAT_RANGE = (40.680, 40.780)
NYC_LNG_RANGE = (-74.010, -73.930)

FALLBACK_NEIGHBORHOODS = [
    "East Village", "West Village", "Lower East Side", "Williamsburg",
    "Chinatown", "Chelsea", "SoHo", "Greenpoint", "Bushwick", "NoHo",
]

FALLBACK_CUISINES = [
    ["New American"], ["Italian"], ["Japanese"], ["Mexican"],
    ["Seafood"], ["Cocktails", "American"], ["Chinese"], ["Mediterranean"],
]


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or hashlib.md5(name.encode()).hexdigest()[:8]


def load_input(path: Path) -> list[dict]:
    if path.suffix.lower() == ".csv":
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return [{"name": row["name"].strip(), "url": row.get("url", "").strip()}
                    for row in reader if row.get("name")]
    if path.suffix.lower() == ".json":
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
            return [{"name": item["name"].strip(), "url": item.get("url", "").strip()}
                    for item in raw if item.get("name")]
    raise ValueError(f"Unsupported input file type: {path.suffix}")


def deterministic_unit(seed: str, salt: str) -> float:
    """Deterministic pseudo-random float in [0, 1) derived from a name + salt."""
    digest = hashlib.md5(f"{seed}:{salt}".encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def fallback_metadata(name: str) -> dict:
    lat = NYC_LAT_RANGE[0] + deterministic_unit(name, "lat") * (NYC_LAT_RANGE[1] - NYC_LAT_RANGE[0])
    lng = NYC_LNG_RANGE[0] + deterministic_unit(name, "lng") * (NYC_LNG_RANGE[1] - NYC_LNG_RANGE[0])
    neighborhood = FALLBACK_NEIGHBORHOODS[int(deterministic_unit(name, "hood") * len(FALLBACK_NEIGHBORHOODS))]
    cuisine = FALLBACK_CUISINES[int(deterministic_unit(name, "cuisine") * len(FALLBACK_CUISINES))]
    price_level = ["$", "$$", "$$$"][int(deterministic_unit(name, "price") * 3)]
    rating = round(4.0 + deterministic_unit(name, "rating") * 0.8, 1)
    return {
        "neighborhood": neighborhood,
        "cuisine": cuisine,
        "price_level": price_level,
        "rating": rating,
        "lat": round(lat, 4),
        "lng": round(lng, 4),
        "notes": f"Auto-generated placeholder notes for {name} — replace with real details once available.",
        "happy_hour_info": "Unknown — no happy hour data available offline.",
    }


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
        return {
            "neighborhood": result.get("formatted_address", "New York, NY").split(",")[1].strip()
            if "," in result.get("formatted_address", "") else "New York",
            "cuisine": [],
            "price_level": price_map.get(result.get("price_level"), "$$"),
            "rating": result.get("rating", 4.3),
            "lat": location.get("lat"),
            "lng": location.get("lng"),
            "notes": result.get("formatted_address", ""),
            "happy_hour_info": "Unknown — not provided by Google Places.",
            "google_url": result.get("url"),
        }
    except (requests.RequestException, KeyError, IndexError) as exc:
        print(f"  Google Places lookup failed for '{name}': {exc}", file=sys.stderr)
        return None


def enrich(entries: list[dict]) -> list[dict]:
    places = []
    for entry in entries:
        name = entry["name"]
        print(f"Enriching: {name}")
        meta = google_places_metadata(name)
        source = "google_places"
        if meta is None:
            meta = fallback_metadata(name)
            source = "offline_fallback"

        places.append({
            "id": slugify(name),
            "name": name,
            "neighborhood": meta.get("neighborhood", "New York"),
            "cuisine": meta.get("cuisine") or ["Unspecified"],
            "price_level": meta.get("price_level", "$$"),
            "rating": meta.get("rating", 4.3),
            "lat": meta.get("lat"),
            "lng": meta.get("lng"),
            "google_url": meta.get("google_url") or entry.get("url") or "",
            "notes": meta.get("notes", ""),
            "happy_hour_info": meta.get("happy_hour_info", "Unknown"),
            "_enrichment_source": source,
        })
    return places


def main():
    parser = argparse.ArgumentParser(description="Enrich a plain list of place names into places.json")
    parser.add_argument("--input", "-i", required=True, help="Path to input CSV or JSON file")
    parser.add_argument("--output", "-o", default="data/places.json", help="Path to write enriched JSON")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    entries = load_input(input_path)
    if not entries:
        print("No entries found in input file.", file=sys.stderr)
        sys.exit(1)

    if not GOOGLE_PLACES_API_KEY:
        print("GOOGLE_PLACES_API_KEY not set — generating offline fallback metadata.\n")

    enriched = enrich(entries)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=2)

    print(f"\nWrote {len(enriched)} places to {output_path}")


if __name__ == "__main__":
    main()
