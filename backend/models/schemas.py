"""Pydantic schemas - ported 1:1 from the dict shapes used throughout the
original Streamlit app.py (place_to_spot(), rule_based_match(), and the
LLM's structured JSON output all produce this same "spot" shape)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Place(BaseModel):
    """Raw dataset record, matches data/places.json exactly."""

    id: str
    name: str
    category: str = "Eats"
    neighborhood: str = ""
    cuisine: list[str] = Field(default_factory=list)
    price_level: str = "$"
    rating: Optional[float] = None
    lat: float
    lng: float
    google_url: str = ""
    notes: str = ""
    happy_hour_info: str = ""
    enrichment_source: Optional[str] = Field(default=None, alias="_enrichment_source")

    class Config:
        populate_by_name = True


class Coordinates(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None


class Links(BaseModel):
    google_maps: str = ""
    reservation_url: Optional[str] = None
    reservation_platform: Optional[str] = None


class ItineraryContext(BaseModel):
    best_time_slot: str = "6:00 PM - 8:00 PM"
    estimated_duration_min: int = 75


class Spot(BaseModel):
    """The recommendation-card shape - what chat/browse/bookmarks/itinerary
    all traffic in. Ported from the dict built by place_to_spot() and
    rule_based_match(), and the schema the LLM is instructed to return."""

    id: str
    name: str
    source: str = "saved"  # "saved" | "fallback"
    is_bookmarked: bool = False
    category: Optional[str] = None
    neighborhood: str = ""
    cuisine: list[str] = Field(default_factory=list)
    price_level: str = "$"
    rating: Optional[float] = None
    match_highlight: str = ""
    coordinates: Coordinates = Field(default_factory=Coordinates)
    links: Links = Field(default_factory=Links)
    itinerary_context: ItineraryContext = Field(default_factory=ItineraryContext)


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    query: str
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    summary: str
    fallback_triggered: bool = False
    spots: list[Spot] = Field(default_factory=list)
    quick_filters: list[str] = Field(default_factory=list)


class SessionStateOut(BaseModel):
    """Consolidated bootstrap payload - not in the original prompt's endpoint
    list, but the frontend needs one place to fetch initial state from
    (bookmarks/itinerary/active-dataset-info) instead of guessing session
    state client-side the way Streamlit's server-rendered model allowed."""

    bookmarks: list[Spot]
    itinerary: list[Spot]
    has_custom_dataset: bool
    active_spot_count: int
    demo_spot_count: int


class ImportResult(BaseModel):
    spots_imported: int
    skipped: int
    message: str
