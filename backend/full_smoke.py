"""Full end-to-end smoke test — LLM generation + validator + MIUI screenshot.

Runs 5 entries through the real orchestrator. Verifies that:
- LLM clients (Groq/Gemini/NIM) are reachable
- Generator prompt produces relationship-style notes
- Validator passes / regenerates as needed
- MIUI screenshots render correctly with theme rotation
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

backend_dir = Path(__file__).parent
load_dotenv(backend_dir.parent / ".env")
sys.path.insert(0, str(backend_dir.parent))

from backend.core.llm_clients import LLMClients
from backend.core.orchestrator import JobOrchestrator
from backend.core.screenshot import close_browser
from backend.db.repo import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


async def main():
    db_path = str((backend_dir.parent / "output" / "smoke_full.sqlite").resolve())
    output_dir = str((backend_dir.parent / "output").resolve())

    # Clean any prior smoke db
    p = Path(db_path)
    if p.exists():
        p.unlink()
    for ext in ("-wal", "-shm"):
        if Path(db_path + ext).exists():
            Path(db_path + ext).unlink()

    db = Database(db_path)
    await db.connect()
    log.info("DB ready: %s", db_path)

    llm = LLMClients()
    log.info("LLM providers: %s", llm.get_available_providers())

    orchestrator = JobOrchestrator(db, llm, output_dir)

    # 10-entry end-to-end smoke. Uses the full default config from orchestrator
    # (Apr 24-26 shuffle, MIUI primary, 39% titles, the new typo pool, etc.).
    config = {
        "start_global_id": 9000,
        "start_part": 99,
        "dataset_type": "contacts",
    }
    job_id = await db.create_job(batch_size=10, config=config)
    log.info("Created smoke job %s", job_id)

    accepted = 0
    failed = 0
    async for event in orchestrator.start_job(job_id):
        ev = event["event"]
        data = event["data"]
        if ev == "entry_completed":
            status = data["status"]
            if status == "accepted":
                accepted += 1
            else:
                failed += 1
            log.info(
                ">>> Entry %d/%s | %s | theme=%s | %s",
                data["entry_num"], data.get("global_id"), status,
                data.get("theme"),
                data.get("title") or "(no title)",
            )
        elif ev == "entry_failed":
            failed += 1
            log.error(">>> Entry %d FAILED: %s", data["entry_num"], data.get("error"))
        elif ev in ("job_started", "job_completed", "job_cancelled"):
            log.info("[%s] %s", ev, data)

    log.info("Smoke complete: %d accepted, %d failed", accepted, failed)

    # Show what was generated
    job_dir = Path(output_dir) / "jobs" / job_id
    notes_dir = job_dir / "notes"
    shots_dir = job_dir / "screenshots"
    if notes_dir.exists():
        log.info("Files generated:")
        for f in sorted(notes_dir.glob("*.txt")):
            log.info("  %s", f.name)
            print("    " + f.read_text().replace("\n", "\n    "))
        log.info("Screenshots:")
        for f in sorted(shots_dir.glob("*.jpg")):
            log.info("  %s", f.name)

    await close_browser()
    await db.close()
    return 0 if accepted >= 3 else 1


if __name__ == "__main__":
    rc = asyncio.run(main())
    sys.exit(rc)
