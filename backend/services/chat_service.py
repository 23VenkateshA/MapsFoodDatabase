"""Ported 1:1 from the LLM orchestration section of app.py: build_system_prompt,
extract_json, call_openrouter, rule_based_match, get_recommendations. Same
prompt text, same two-tier provider-selection/fallback structure, same
offline keyword scoring. The 75-vs-90-minute itinerary duration
inconsistency between this file's offline path and place_to_spot() has been
aligned to 75 (not preserved as a bug), per explicit instruction during the
migration - everything else here is an exact behavioral port."""

from __future__ import annotations

import json
import os
import re

from .places_data import _real_happy_hour

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = "openai/gpt-4o-mini"

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


def build_system_prompt(saved_places: list[dict], location_context: str | None = None) -> str:
    compact = [
        {k: p[k] for k in ("id", "name", "neighborhood", "cuisine", "price_level",
                            "rating", "lat", "lng", "notes", "happy_hour_info")}
        for p in saved_places
    ]
    prompt = SYSTEM_PROMPT_TEMPLATE.format(saved_places_json=json.dumps(compact, indent=2))
    if location_context:
        prompt += f"\n\nUser's current location context: {location_context} Prefer nearby spots when relevant.\n"
    return prompt


def extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    return json.loads(text)


def call_openrouter(user_query: str, system_prompt: str, history: list[dict]) -> dict:
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


def rule_based_match(user_query: str, saved_places: list[dict], bookmarked_ids: set[str]) -> dict:
    """Offline fallback: keyword match against the saved list, no LLM required."""
    query_lower = user_query.lower()
    keywords = re.findall(r"[a-z]+", query_lower)

    def score(place: dict) -> int:
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
            "is_bookmarked": p["id"] in bookmarked_ids,
            "neighborhood": p["neighborhood"],
            "cuisine": p["cuisine"],
            "price_level": p["price_level"],
            "rating": p["rating"],
            "match_highlight": _real_happy_hour(p.get("happy_hour_info")) or p.get("notes", ""),
            "coordinates": {"lat": p["lat"], "lng": p["lng"]},
            "links": {"google_maps": p.get("google_url", ""), "reservation_url": None, "reservation_platform": None},
            "itinerary_context": {"best_time_slot": "6:00 PM - 8:00 PM", "estimated_duration_min": 75},
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


def get_recommendations(
    user_query: str,
    saved_places: list[dict],
    history: list[dict],
    bookmarked_ids: set[str],
    location_context: str | None = None,
) -> dict:
    system_prompt = build_system_prompt(saved_places, location_context)
    if OPENROUTER_API_KEY:
        try:
            result = call_openrouter(user_query, system_prompt, history)
            for spot in result.get("spots", []):
                spot["is_bookmarked"] = spot.get("id") in bookmarked_ids
            return result
        except Exception:  # noqa: BLE001 - same broad catch as the original, then degrade gracefully
            pass
    return rule_based_match(user_query, saved_places, bookmarked_ids)
