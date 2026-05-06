"""Migration: add language + note_text_en columns to existing database.

Run once after deploying the Hindi feature:
    python -m backend.db.migrate_hindi
"""

import asyncio
import logging
import os
from pathlib import Path

import aiosqlite

log = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", str(Path(__file__).parent.parent.parent / "output" / "app.sqlite"))


async def migrate():
    log.info("Running Hindi migration on: %s", DB_PATH)
    async with aiosqlite.connect(DB_PATH) as db:
        # Check existing columns
        cursor = await db.execute("PRAGMA table_info(entries)")
        cols = {row[1] for row in await cursor.fetchall()}

        added = []
        if "language" not in cols:
            await db.execute("ALTER TABLE entries ADD COLUMN language TEXT NOT NULL DEFAULT 'english'")
            added.append("entries.language")
        if "note_text_en" not in cols:
            await db.execute("ALTER TABLE entries ADD COLUMN note_text_en TEXT")
            added.append("entries.note_text_en")

        await db.commit()

    if added:
        log.info("Migration complete. Added columns: %s", ", ".join(added))
    else:
        log.info("Nothing to migrate — columns already exist.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(migrate())
