from __future__ import annotations

from fastapi import APIRouter, Depends

from deps import get_session_id
from models.schemas import ItineraryStop, Spot
from services import itinerary_service, store

router = APIRouter(prefix="/itinerary", tags=["itinerary"])


def _scheduled(session_id: str) -> list[dict]:
    return itinerary_service.build_schedule(store.get_itinerary(session_id))


@router.get("", response_model=list[ItineraryStop])
def list_itinerary(session_id: str = Depends(get_session_id)) -> list[dict]:
    return _scheduled(session_id)


@router.post("", response_model=list[ItineraryStop])
def add_itinerary_stop(spot: Spot, session_id: str = Depends(get_session_id)) -> list[dict]:
    """Mirrors `st.session_state.itinerary.append(spot)` - appended in order,
    same as the original plain list (the "+ Itinerary" button was already
    disabled client-side once a spot's id was present, so this doesn't
    re-implement that guard server-side)."""
    store.add_itinerary_stop(session_id, spot.model_dump())
    return _scheduled(session_id)


@router.delete("/{spot_id}", response_model=list[ItineraryStop])
def remove_itinerary_stop(spot_id: str, session_id: str = Depends(get_session_id)) -> list[dict]:
    store.remove_itinerary_stop(session_id, spot_id)
    return _scheduled(session_id)


@router.post("/reset", response_model=list[ItineraryStop])
def reset_itinerary(session_id: str = Depends(get_session_id)) -> list[dict]:
    """Mirrors the "Clear itinerary" button."""
    store.clear_itinerary(session_id)
    return _scheduled(session_id)
