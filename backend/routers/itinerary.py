from __future__ import annotations

from fastapi import APIRouter, Depends

from deps import get_session_id
from models.schemas import Spot
from services import store

router = APIRouter(prefix="/itinerary", tags=["itinerary"])


@router.get("", response_model=list[Spot])
def list_itinerary(session_id: str = Depends(get_session_id)) -> list[dict]:
    return store.get_itinerary(session_id)


@router.post("", response_model=list[Spot])
def add_itinerary_stop(spot: Spot, session_id: str = Depends(get_session_id)) -> list[dict]:
    """Mirrors `st.session_state.itinerary.append(spot)` - appended in order,
    same as the original plain list (the "+ Itinerary" button was already
    disabled client-side once a spot's id was present, so this doesn't
    re-implement that guard server-side)."""
    store.add_itinerary_stop(session_id, spot.model_dump())
    return store.get_itinerary(session_id)


@router.delete("/{spot_id}", response_model=list[Spot])
def remove_itinerary_stop(spot_id: str, session_id: str = Depends(get_session_id)) -> list[dict]:
    store.remove_itinerary_stop(session_id, spot_id)
    return store.get_itinerary(session_id)


@router.post("/reset", response_model=list[Spot])
def reset_itinerary(session_id: str = Depends(get_session_id)) -> list[dict]:
    """Mirrors the "Clear itinerary" button."""
    store.clear_itinerary(session_id)
    return store.get_itinerary(session_id)
