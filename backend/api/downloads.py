"""Downloads API — .txt, .jpg, .zip endpoints."""

import io
import logging
import os
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["downloads"])


@router.get("/entries/{entry_id}/text")
async def download_text(entry_id: str, request: Request):
    """Download .txt file for an entry."""
    db = request.app.state.db
    entry = await db.get_entry(entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")
    if not entry.get("txt_path") or not os.path.exists(entry["txt_path"]):
        raise HTTPException(404, "Text file not found")
    return FileResponse(
        entry["txt_path"],
        filename=entry.get("txt_filename", f"{entry_id}.txt"),
        media_type="text/plain",
    )


@router.get("/entries/{entry_id}/image")
async def download_image(entry_id: str, request: Request):
    """Download .jpg file for an entry."""
    db = request.app.state.db
    entry = await db.get_entry(entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")
    if not entry.get("jpg_path") or not os.path.exists(entry["jpg_path"]):
        raise HTTPException(404, "Image file not found")
    return FileResponse(
        entry["jpg_path"],
        filename=entry.get("jpg_filename", f"{entry_id}.jpg"),
        media_type="image/jpeg",
    )


@router.get("/entries/{entry_id}/bundle.zip")
async def download_entry_bundle(entry_id: str, request: Request):
    """Download .txt + .jpg as a zip for a single entry."""
    db = request.app.state.db
    entry = await db.get_entry(entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        if entry.get("txt_path") and os.path.exists(entry["txt_path"]):
            zf.write(entry["txt_path"], entry.get("txt_filename", f"{entry_id}.txt"))
        if entry.get("jpg_path") and os.path.exists(entry["jpg_path"]):
            zf.write(entry["jpg_path"], entry.get("jpg_filename", f"{entry_id}.jpg"))

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{entry_id}_bundle.zip"'},
    )


@router.get("/jobs/{job_id}/bundle.zip")
async def download_job_bundle(job_id: str, request: Request, status: str = "accepted"):
    """Download all entries for a job as notes/ + screenshots/ zip."""
    db = request.app.state.db
    entries = await db.list_entries(job_id, status=status, limit=10000)

    if not entries:
        raise HTTPException(404, "No entries found")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for entry in entries:
            if entry.get("txt_path") and os.path.exists(entry["txt_path"]):
                zf.write(
                    entry["txt_path"],
                    f"notes/{entry.get('txt_filename', str(entry['id']) + '.txt')}",
                )
            if entry.get("jpg_path") and os.path.exists(entry["jpg_path"]):
                zf.write(
                    entry["jpg_path"],
                    f"screenshots/{entry.get('jpg_filename', str(entry['id']) + '.jpg')}",
                )

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="job_{job_id}_bundle.zip"'},
    )
