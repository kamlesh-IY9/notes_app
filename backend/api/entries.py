"""Entries API — list, detail, edit, regenerate entries."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/entries", tags=["entries"])


@router.get("/by-job/{job_id}")
async def list_entries(
    job_id: str,
    request: Request,
    status: Optional[str] = None,
    app_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """List entries for a job with optional filters."""
    db = request.app.state.db
    entries = await db.list_entries(
        job_id, status=status, app_type=app_type,
        limit=limit, offset=offset,
    )
    total = await db.count_entries(job_id, status=status)
    return {"entries": entries, "total": total}


@router.get("/{entry_id}")
async def get_entry(entry_id: str, request: Request):
    """Get full entry detail."""
    db = request.app.state.db
    entry = await db.get_entry(entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")
    # Parse JSON fields
    if entry.get("validation_json"):
        entry["validation"] = json.loads(entry["validation_json"])
    if entry.get("persona_json"):
        entry["persona"] = json.loads(entry["persona_json"])
    return entry


class EntryUpdateRequest(BaseModel):
    note_text: Optional[str] = None
    status: Optional[str] = None


@router.patch("/{entry_id}")
async def update_entry(entry_id: str, req: EntryUpdateRequest, request: Request):
    """Update entry text or status."""
    db = request.app.state.db
    entry = await db.get_entry(entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")

    updates = {}
    if req.note_text is not None:
        updates["note_text"] = req.note_text
    if req.status is not None:
        updates["status"] = req.status

    if updates:
        await db.update_entry(entry_id, **updates)

    return {"status": "updated"}


@router.post("/{entry_id}/regenerate")
async def regenerate_entry(entry_id: str, request: Request):
    """Regenerate a single entry (re-uses the same ID slot)."""
    db = request.app.state.db
    entry = await db.get_entry(entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")

    # Mark as pending for regeneration
    await db.update_entry(entry_id, status="pending")
    return {"status": "queued_for_regeneration", "entry_id": entry_id}
