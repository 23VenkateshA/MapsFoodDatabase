from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from deps import get_session_id
from models.schemas import ImportResult
from services import import_service, store

router = APIRouter(prefix="/import", tags=["import"])


@router.post("", response_model=ImportResult)
async def import_places(file: UploadFile, session_id: str = Depends(get_session_id)) -> dict:
    """Ported feature (not in the original prompt's endpoint list, added per
    explicit confirmation): CSV (Google Maps list export) is geocoded live
    via free Nominatim; Google Takeout Saved Places.json already has
    coordinates and imports instantly. Either way, the result replaces the
    session's *entire* active dataset, mirroring uploaded_places in the
    original app - not merged with the demo dataset."""
    raw_bytes = await file.read()
    filename = (file.filename or "").lower()

    try:
        if filename.endswith(".json"):
            places, skipped = import_service.parse_uploaded_json(raw_bytes)
        else:
            places, skipped = import_service.parse_uploaded_csv(raw_bytes)
    except import_service.ImportError_ as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    store.set_uploaded_places(session_id, places)

    message = f"{len(places)} spots imported"
    if skipped:
        message += f" ({skipped} entries skipped — missing name or coordinates)"
    return {"spots_imported": len(places), "skipped": skipped, "message": message}


@router.post("/reset")
def remove_uploaded_dataset(session_id: str = Depends(get_session_id)) -> dict:
    """Mirrors the "✕ Remove uploaded data (use demo dataset)" button."""
    store.clear_uploaded_places(session_id)
    return {"status": "reset"}
