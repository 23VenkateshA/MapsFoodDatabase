from __future__ import annotations

from fastapi import APIRouter, Depends

from deps import get_session_id
from models.schemas import SessionStateOut
from services import itinerary_service, store
from services.places_data import load_demo_places

router = APIRouter(tags=["session"])


@router.get("/session", response_model=SessionStateOut)
def get_session_state(session_id: str = Depends(get_session_id)) -> dict:
    """Consolidated bootstrap payload for the frontend on first load - not
    in the original endpoint list, but Streamlit's server-rendered model
    meant the app always knew its own state; a React frontend needs one
    place to fetch it from instead of assuming empty."""
    uploaded = store.get_uploaded_places(session_id)
    active = uploaded if uploaded else load_demo_places()
    return {
        "bookmarks": store.get_bookmarks(session_id),
        "itinerary": itinerary_service.build_schedule(store.get_itinerary(session_id)),
        "has_custom_dataset": uploaded is not None,
        "active_spot_count": len(active),
        "demo_spot_count": len(load_demo_places()),
    }


@router.post("/session/reset")
def reset_session(session_id: str = Depends(get_session_id)) -> dict:
    """Mirrors the "Reset entire session" button: clears bookmarks,
    itinerary, and any uploaded dataset. Does not re-seed the demo data -
    matches the original (seeding only ever fires for a session_state key
    that has never existed, not an emptied one)."""
    store.reset_session(session_id)
    return {"status": "reset"}
