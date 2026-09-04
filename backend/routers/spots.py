from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from deps import get_session_id
from models.schemas import Spot
from services import geo, store
from services.places_data import filter_places, place_to_spot

router = APIRouter(tags=["spots"])


@router.get("/spots", response_model=list[Spot])
def get_spots(
    q: Optional[str] = None,
    category: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    address_id: Optional[str] = None,
    radius_miles: Optional[float] = None,
    sort: Optional[str] = None,  # "distance" - anything else (including unset) keeps original order
    session_id: str = Depends(get_session_id),
) -> list[dict]:
    """Ported 1:1 from render_browse_view()'s filter_places() call, extended
    with an optional distance anchor: pass either address_id (a saved
    address) or raw lat/lng to get distance_miles/walk_minutes annotated
    onto each result, radius_miles to drop anything farther, and
    sort=distance to order by it. No anchor -> behaves exactly as before."""
    active_places = store.get_active_places(session_id)
    bookmarked_ids = store.get_bookmark_ids(session_id)
    filtered = filter_places(active_places, q, category)
    spots = [place_to_spot(p, bookmarked_ids) for p in filtered]

    anchor = None
    if address_id:
        addr = store.get_address(session_id, address_id)
        if addr is None:
            raise HTTPException(status_code=404, detail="Address not found.")
        anchor = (addr["lat"], addr["lng"])
    elif lat is not None and lng is not None:
        anchor = (lat, lng)

    if anchor is not None:
        for spot in spots:
            coords = spot["coordinates"]
            if coords["lat"] is None or coords["lng"] is None:
                continue
            miles = geo.haversine_miles(anchor[0], anchor[1], coords["lat"], coords["lng"])
            spot["distance_miles"] = round(miles, 2)
            spot["walk_minutes"] = geo.walk_minutes(miles)

        if radius_miles is not None:
            spots = [s for s in spots if s.get("distance_miles") is not None and s["distance_miles"] <= radius_miles]

        if sort == "distance":
            spots.sort(key=lambda s: s["distance_miles"] if s.get("distance_miles") is not None else float("inf"))

    return spots


@router.get("/spots/{spot_id}", response_model=Spot)
def get_spot(spot_id: str, session_id: str = Depends(get_session_id)) -> dict:
    active_places = store.get_active_places(session_id)
    bookmarked_ids = store.get_bookmark_ids(session_id)
    for place in active_places:
        if place["id"] == spot_id:
            return place_to_spot(place, bookmarked_ids)
    raise HTTPException(status_code=404, detail=f"No spot with id '{spot_id}'")
