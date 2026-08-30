from __future__ import annotations

from fastapi import APIRouter, Depends

from deps import get_session_id
from models.schemas import Spot
from services import store

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


@router.get("", response_model=list[Spot])
def list_bookmarks(session_id: str = Depends(get_session_id)) -> list[dict]:
    return store.get_bookmarks(session_id)


@router.post("", response_model=list[Spot])
def add_bookmark(spot: Spot, session_id: str = Depends(get_session_id)) -> list[dict]:
    """Accepts the full spot payload the frontend already has on the card -
    mirrors `st.session_state.bookmarks[sid] = spot` exactly, since a
    fallback/LLM-suggested spot may not exist in the base dataset at all."""
    store.add_bookmark(session_id, spot.model_dump())
    return store.get_bookmarks(session_id)


@router.delete("/{spot_id}", response_model=list[Spot])
def remove_bookmark(spot_id: str, session_id: str = Depends(get_session_id)) -> list[dict]:
    store.remove_bookmark(session_id, spot_id)
    return store.get_bookmarks(session_id)


@router.post("/reset", response_model=list[Spot])
def reset_bookmarks(session_id: str = Depends(get_session_id)) -> list[dict]:
    """Mirrors the "Clear bookmarks" button - empties the list, does not re-seed."""
    store.clear_bookmarks(session_id)
    return store.get_bookmarks(session_id)
