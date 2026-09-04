"""Computes per-stop scheduling for the itinerary: real arrival/departure
clock times plus an estimated walk time between consecutive stops, so the
frontend can render a timeline instead of a flat list.

There is no user-editable arrival-time override anywhere in this app (the
original Streamlit app never had one either), so stops are simply scheduled
back-to-back starting from the first stop's own best_time_slot. Because of
that, the "not enough travel time" warning described in the feature spec
(which assumes a user-set arrival time) doesn't have anything to compare
against here - instead, timing_warning flags a stop whose *computed*
arrival falls outside its own best_time_slot window (e.g. a cafe's 9-11 AM
slot getting pushed to 6 PM by earlier stops), which is the closest
equivalent derivable from data that actually exists."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from . import geo

DEFAULT_START = "6:00 PM"
TIME_RE = re.compile(r"(\d{1,2}):(\d{2})\s*(AM|PM)", re.IGNORECASE)


def _parse_clock(text: str) -> datetime | None:
    match = TIME_RE.search(text or "")
    if not match:
        return None
    hour, minute, meridiem = int(match.group(1)), int(match.group(2)), match.group(3).upper()
    if hour == 12:
        hour = 0
    if meridiem == "PM":
        hour += 12
    return datetime(2000, 1, 1, hour, minute)


def _format_clock(dt: datetime) -> str:
    return dt.strftime("%I:%M %p").lstrip("0")


def _window(best_time_slot: str) -> tuple[datetime, datetime] | None:
    parts = (best_time_slot or "").split("-")
    if len(parts) != 2:
        return None
    start, end = _parse_clock(parts[0]), _parse_clock(parts[1])
    if start is None or end is None:
        return None
    if end < start:
        end += timedelta(days=1)
    return start, end


def build_schedule(spots: list[dict]) -> list[dict]:
    """spots is the ordered list of Spot dicts already stored for the
    itinerary (store.get_itinerary's output) - this only adds timing, it
    doesn't change ordering or persistence."""
    if not spots:
        return []

    first_window = _window((spots[0].get("itinerary_context") or {}).get("best_time_slot", ""))
    clock = first_window[0] if first_window else (_parse_clock(DEFAULT_START) or datetime(2000, 1, 1, 18, 0))

    stops = []
    for i, spot in enumerate(spots):
        ctx = spot.get("itinerary_context") or {}
        duration = ctx.get("estimated_duration_min", 75)
        arrival = clock
        departure = arrival + timedelta(minutes=duration)

        warning = None
        window = _window(ctx.get("best_time_slot", ""))
        if window and not (window[0] <= arrival <= window[1]):
            warning = f"Arrives outside this spot's usual best time ({ctx.get('best_time_slot')})"

        travel_minutes = None
        if i + 1 < len(spots):
            coords = spot.get("coordinates") or {}
            next_coords = spots[i + 1].get("coordinates") or {}
            if coords.get("lat") is not None and next_coords.get("lat") is not None:
                miles = geo.haversine_miles(coords["lat"], coords["lng"], next_coords["lat"], next_coords["lng"])
                travel_minutes = geo.walk_minutes(miles)
            clock = departure + timedelta(minutes=travel_minutes or 0)

        stops.append(
            {
                "spot": spot,
                "arrival_time": _format_clock(arrival),
                "departure_time": _format_clock(departure),
                "travel_to_next_minutes": travel_minutes,
                "timing_warning": warning,
            }
        )

    return stops
