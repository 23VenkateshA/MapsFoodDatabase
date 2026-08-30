from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from deps import get_session_id
from models.schemas import Spot
from services import store
from services.places_data import filter_places, place_to_spot

router = APIRouter(tags=["spots"])


@router.get("/spots", response_model=list[Spot])
def get_spots(
    q: Optional[str] = None,
    category: Optional[str] = None,
    session_id: str = Depends(get_session_id),
) -> list[dict]:
    """Ported 1:1 from render_browse_view()'s filter_places() call - returns
    every match (no server-side pagination), same as the original: the
    Streamlit app capped *card display* to 40 client-side while still
    plotting every match on the map, so the API itself stays uncapped and
    the frontend owns that same display-only truncation."""
    active_places = store.get_active_places(session_id)
    bookmarked_ids = store.get_bookmark_ids(session_id)
    filtered = filter_places(active_places, q, category)
    return [place_to_spot(p, bookmarked_ids) for p in filtered]


@router.get("/spots/{spot_id}", response_model=Spot)
def get_spot(spot_id: str, session_id: str = Depends(get_session_id)) -> dict:
    active_places = store.get_active_places(session_id)
    bookmarked_ids = store.get_bookmark_ids(session_id)
    for place in active_places:
        if place["id"] == spot_id:
            return place_to_spot(place, bookmarked_ids)
    raise HTTPException(status_code=404, detail=f"No spot with id '{spot_id}'")
