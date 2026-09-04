"""FastAPI entrypoint. Run with: uvicorn main:app --reload --port 8000"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from routers import addresses, bookmarks, chat, import_, itinerary, session, spots  # noqa: E402
from services.store import init_db  # noqa: E402

app = FastAPI(title="NYC Dining Concierge API")

allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,  # required so the session_id cookie round-trips from the frontend origin
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(chat.router)
app.include_router(spots.router)
app.include_router(bookmarks.router)
app.include_router(itinerary.router)
app.include_router(session.router)
app.include_router(import_.router)
app.include_router(addresses.router)
