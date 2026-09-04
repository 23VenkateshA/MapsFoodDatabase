from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from deps import get_session_id
from models.schemas import Address, AddressIn
from services import geo, store

router = APIRouter(prefix="/addresses", tags=["addresses"])


@router.get("", response_model=list[Address])
def list_addresses(session_id: str = Depends(get_session_id)) -> list[dict]:
    return store.get_addresses(session_id)


@router.post("", response_model=Address)
def create_address(payload: AddressIn, session_id: str = Depends(get_session_id)) -> dict:
    coords = geo.geocode_address(payload.address)
    if coords is None:
        raise HTTPException(status_code=422, detail=f"Could not find a location for '{payload.address}'.")
    address_id = str(uuid.uuid4())
    lat, lng = coords
    store.add_address(session_id, address_id, payload.label.strip() or "Address", payload.address.strip(), lat, lng)
    address = store.get_address(session_id, address_id)
    assert address is not None
    return address


@router.delete("/{address_id}", response_model=list[Address])
def remove_address(address_id: str, session_id: str = Depends(get_session_id)) -> list[dict]:
    store.delete_address(session_id, address_id)
    return store.get_addresses(session_id)


@router.put("/{address_id}/default", response_model=list[Address])
def make_default(address_id: str, session_id: str = Depends(get_session_id)) -> list[dict]:
    if store.get_address(session_id, address_id) is None:
        raise HTTPException(status_code=404, detail="Address not found.")
    store.set_default_address(session_id, address_id)
    return store.get_addresses(session_id)
