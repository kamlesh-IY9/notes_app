"""Jobs API — CRUD + SSE stream for generation jobs."""

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class JobCreateRequest(BaseModel):
    dataset_type: str = Field(default="people_relationships")
    batch_size: int = Field(default=10, ge=1, le=5000)
    app_distribution: dict = Field(
        default={"apple_notes": 50, "google_keep": 30, "samsung_notes": 20}
    )
    dark_mode_share: int = Field(default=25, ge=0, le=100)
    title_share: int = Field(default=70, ge=0, le=100)
    date_min: str = Field(default="2021-04-25")
    date_max: str = Field(default="2026-04-25")
    connectivity_distribution: dict = Field(
        default={"wifi_cellular": 60, "cellular_only": 25, "wifi_only": 10, "no_service": 5}
    )
    contact_app_distribution: dict = Field(
        default={"miui_notes": 50, "apple_notes": 30, "samsung_notes": 12, "google_keep": 8}
    )
    start_global_id: int = Field(default=1100)
    start_part: int = Field(default=32)


@router.post("")
async def create_job(req: JobCreateRequest, request: Request):
    """Create a new generation job."""
    db = request.app.state.db
    config = req.model_dump()
    job_id = await db.create_job(req.batch_size, config)
    return {"job_id": job_id, "status": "pending"}


@router.get("")
async def list_jobs(request: Request):
    """List all jobs."""
    db = request.app.state.db
    jobs = await db.list_jobs()
    return {"jobs": jobs}


@router.get("/{job_id}")
async def get_job(job_id: str, request: Request):
    """Get job details."""
    db = request.app.state.db
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.get("/{job_id}/events")
async def job_events(job_id: str, request: Request):
    """SSE stream for job progress events."""
    db = request.app.state.db
    orchestrator = request.app.state.orchestrator

    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    async def event_generator():
        try:
            async for event in orchestrator.start_job(job_id):
                if await request.is_disconnected():
                    break
                yield {
                    "event": event["event"],
                    "data": json.dumps(event["data"]),
                }
        except Exception as e:
            log.error("SSE stream error: %s", e, exc_info=True)
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e)}),
            }

    return EventSourceResponse(event_generator())


@router.post("/{job_id}/pause")
async def pause_job(job_id: str, request: Request):
    """Pause a running job."""
    orchestrator = request.app.state.orchestrator
    orchestrator.pause_job(job_id)
    await request.app.state.db.update_job_status(job_id, "paused")
    return {"status": "paused"}


@router.post("/{job_id}/resume")
async def resume_job(job_id: str, request: Request):
    """Resume a paused job."""
    orchestrator = request.app.state.orchestrator
    orchestrator.resume_job(job_id)
    await request.app.state.db.update_job_status(job_id, "running")
    return {"status": "running"}


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str, request: Request):
    """Cancel a running job."""
    orchestrator = request.app.state.orchestrator
    orchestrator.cancel_job(job_id)
    return {"status": "cancelling"}


@router.delete("/{job_id}")
async def delete_job(job_id: str, request: Request):
    """Delete a job and its entries."""
    db = request.app.state.db
    await db.delete_job(job_id)
    return {"status": "deleted"}
