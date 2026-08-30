"""Ported 1:1 from parse_uploaded_csv() / parse_uploaded_json() in app.py.
Same Google-Maps-CSV / Google-Takeout-JSON parsing, same Nominatim geocoding
with synthetic-coordinate fallback, same category default ("Eats", since
uploaded lists don't carry the demo dataset's Bar/Cafe/Eats split)."""

from __future__ import annotations

import csv
import io
import json
import time

import requests

from . import enrich_service

UPLOAD_CATEGORY = "Eats"


class ImportError_(ValueError):
    """Distinct name to avoid shadowing the builtin ImportError."""


def parse_uploaded_csv(raw_bytes: bytes, progress_cb=None) -> tuple[list[dict], int]:
    if not raw_bytes:
        raise ImportError_("The uploaded file is empty.")
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportError_("Could not read this file as UTF-8 text.") from exc

    try:
        reader = csv.DictReader(io.StringIO(text))
        fieldnames = reader.fieldnames or []
    except csv.Error as exc:
        raise ImportError_("Could not parse this as a CSV file.") from exc

    fieldmap = {(fn or "").strip().lower(): fn for fn in fieldnames}
    name_field = fieldmap.get("title") or fieldmap.get("name")
    if not name_field:
        raise ImportError_("No 'Title' or 'name' column found — expected a Google Maps list export format.")
    url_field = fieldmap.get("url")

    rows = []
    for row in reader:
        name = (row.get(name_field) or "").strip()
        if not name:
            continue
        url = (row.get(url_field) or "").strip() if url_field else ""
        rows.append({"name": name, "url": url, "category": UPLOAD_CATEGORY})

    if not rows:
        raise ImportError_("No places found in the uploaded CSV.")

    rows = enrich_service.dedupe(rows)
    enrich_service.assign_unique_ids(rows)

    session = requests.Session()
    n = len(rows)
    places = []
    for i, row in enumerate(rows):
        name = row["name"]
        geo = enrich_service.nominatim_geocode(session, name)
        time.sleep(enrich_service.NOMINATIM_DELAY_SECONDS)
        if geo:
            lat, lng, neighborhood = geo["lat"], geo["lng"], geo.get("neighborhood")
            source = "nominatim"
        else:
            synth = enrich_service.synthetic_location(name)
            lat, lng, neighborhood = synth["lat"], synth["lng"], synth["neighborhood"]
            source = "offline_fallback"

        price_level, rating = enrich_service.placeholder_price_and_rating(name)
        places.append({
            "id": row["id"],
            "name": name,
            "category": UPLOAD_CATEGORY,
            "neighborhood": neighborhood or "New York",
            "cuisine": enrich_service.classify_cuisine(name, UPLOAD_CATEGORY),
            "price_level": price_level,
            "rating": rating,
            "lat": round(float(lat), 4),
            "lng": round(float(lng), 4),
            "google_url": row.get("url", ""),
            "notes": "Imported from your uploaded CSV.",
            "happy_hour_info": "Not listed — check with the venue for current happy hour specials.",
            "_enrichment_source": source,
        })
        if progress_cb is not None:
            progress_cb(i + 1, n, name)

    return places, 0


def parse_uploaded_json(raw_bytes: bytes) -> tuple[list[dict], int]:
    if not raw_bytes:
        raise ImportError_("The uploaded file is empty.")
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ImportError_("Could not parse this as a JSON file.") from exc

    if not isinstance(data, dict) or data.get("type") != "FeatureCollection" or not data.get("features"):
        raise ImportError_(
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
        raise ImportError_("No usable places found in this file (entries are missing name/coordinates).")

    enrich_service.assign_unique_ids(raw_entries)

    places = []
    for entry in raw_entries:
        name = entry["name"]
        price_level, rating = enrich_service.placeholder_price_and_rating(name)
        places.append({
            "id": entry["id"],
            "name": name,
            "category": UPLOAD_CATEGORY,
            "neighborhood": entry.get("address") or "New York",
            "cuisine": enrich_service.classify_cuisine(name, UPLOAD_CATEGORY),
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
