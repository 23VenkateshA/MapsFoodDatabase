from __future__ import annotations

from fastapi import APIRouter, Depends

from deps import get_session_id
from models.schemas import ChatRequest, ChatResponse
from services import chat_service, store

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def post_chat(payload: ChatRequest, session_id: str = Depends(get_session_id)) -> dict:
    active_places = store.get_active_places(session_id)
    bookmarked_ids = store.get_bookmark_ids(session_id)
    history = [{"role": m.role, "content": m.content} for m in payload.history]

    location_context = None
    if payload.near_label and payload.near_lat is not None and payload.near_lng is not None:
        radius = f" within about {payload.radius_miles} miles" if payload.radius_miles else ""
        location_context = f"searching near {payload.near_label}{radius} (lat {payload.near_lat}, lng {payload.near_lng})."

    return chat_service.get_recommendations(payload.query, active_places, history, bookmarked_ids, location_context)
