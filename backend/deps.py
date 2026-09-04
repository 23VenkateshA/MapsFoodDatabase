"""Shared FastAPI dependency: resolves (and issues, if missing) the
session_id cookie that scopes bookmarks/itinerary/uploaded-dataset storage.
Session cookies are how this REST API differentiates "browser sessions" now
that there's no single long-lived Streamlit process holding st.session_state
per WebSocket connection."""

from __future__ import annotations

import os
import uuid

from fastapi import Request, Response

from services import store

SESSION_COOKIE_NAME = "nyc_concierge_session"

# The frontend (vercel.app) and backend (onrender.com) are different sites in
# production, so the session cookie needs SameSite=None; Secure to survive a
# cross-site fetch at all - browsers silently drop a SameSite=Lax cookie set
# from a cross-site response, which made every request look like a brand-new
# session server-side (re-seeding the demo data every time). Locally
# frontend/backend are "same site" (same host, different port), where Lax
# works fine and None wouldn't (it requires Secure, i.e. HTTPS). RENDER is a
# built-in env var Render sets on every deploy, so this needs no manual
# config either way.
IS_PRODUCTION = os.getenv("RENDER") is not None


def get_session_id(request: Request, response: Response) -> str:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        session_id = str(uuid.uuid4())
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            httponly=True,
            samesite="none" if IS_PRODUCTION else "lax",
            secure=IS_PRODUCTION,
            max_age=60 * 60 * 24 * 365,
        )
    store.ensure_session_seeded(session_id)
    return session_id
