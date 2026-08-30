"""Shared FastAPI dependency: resolves (and issues, if missing) the
session_id cookie that scopes bookmarks/itinerary/uploaded-dataset storage.
Session cookies are how this REST API differentiates "browser sessions" now
that there's no single long-lived Streamlit process holding st.session_state
per WebSocket connection."""

from __future__ import annotations

import uuid

from fastapi import Request, Response

from services import store

SESSION_COOKIE_NAME = "nyc_concierge_session"


def get_session_id(request: Request, response: Response) -> str:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        session_id = str(uuid.uuid4())
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 365,
        )
    store.ensure_session_seeded(session_id)
    return session_id
