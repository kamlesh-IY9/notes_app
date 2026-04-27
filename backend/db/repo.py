"""SQLite data access layer for jobs, entries, and dedup registry."""

import aiosqlite
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


DB_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class Database:
    """Async SQLite wrapper for the notes generator."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def connect(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        # Initialize schema
        schema = DB_SCHEMA_PATH.read_text()
        await self._db.executescript(schema)
        await self._db.commit()

    async def close(self):
        if self._db:
            await self._db.close()

    # ── Jobs ──────────────────────────────────────────────

    async def create_job(self, batch_size: int, config: dict) -> str:
        job_id = uuid.uuid4().hex[:12]
        now = datetime.utcnow().isoformat()
        await self._db.execute(
            """INSERT INTO jobs (id, status, batch_size, config, total, created_at, updated_at)
               VALUES (?, 'pending', ?, ?, ?, ?, ?)""",
            (job_id, batch_size, json.dumps(config), batch_size, now, now),
        )
        # Create checkpoint
        start_id = config.get("start_global_id", 1100)
        start_part = config.get("start_part", 32)
        await self._db.execute(
            """INSERT INTO checkpoints (job_id, last_entry, next_global_id, next_part)
               VALUES (?, 0, ?, ?)""",
            (job_id, start_id, start_part),
        )
        await self._db.commit()
        return job_id

    async def get_job(self, job_id: str) -> Optional[dict]:
        cursor = await self._db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def list_jobs(self) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def update_job_status(self, job_id: str, status: str, **counters):
        sets = ["status = ?", "updated_at = ?"]
        vals = [status, datetime.utcnow().isoformat()]
        for k, v in counters.items():
            sets.append(f"{k} = ?")
            vals.append(v)
        vals.append(job_id)
        await self._db.execute(
            f"UPDATE jobs SET {', '.join(sets)} WHERE id = ?", vals
        )
        await self._db.commit()

    async def increment_job_counter(self, job_id: str, counter: str, amount: int = 1):
        await self._db.execute(
            f"UPDATE jobs SET {counter} = {counter} + ?, updated_at = ? WHERE id = ?",
            (amount, datetime.utcnow().isoformat(), job_id),
        )
        await self._db.commit()

    async def delete_job(self, job_id: str):
        await self._db.execute("DELETE FROM entries WHERE job_id = ?", (job_id,))
        await self._db.execute("DELETE FROM checkpoints WHERE job_id = ?", (job_id,))
        await self._db.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        await self._db.commit()

    # ── Entries ───────────────────────────────────────────

    async def create_entry(self, job_id: str, entry_num: int, global_id: int,
                           part_num: int, **kwargs) -> str:
        entry_id = uuid.uuid4().hex[:16]
        cols = ["id", "job_id", "entry_num", "global_id", "part_num"]
        vals = [entry_id, job_id, entry_num, global_id, part_num]
        for k, v in kwargs.items():
            cols.append(k)
            if isinstance(v, dict):
                vals.append(json.dumps(v))
            else:
                vals.append(v)
        placeholders = ", ".join(["?"] * len(cols))
        col_str = ", ".join(cols)
        await self._db.execute(
            f"INSERT INTO entries ({col_str}) VALUES ({placeholders})", vals
        )
        await self._db.commit()
        return entry_id

    async def get_entry(self, entry_id: str) -> Optional[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM entries WHERE id = ?", (entry_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d.pop("embedding", None)
        return d

    async def list_entries(self, job_id: str, status: Optional[str] = None,
                           app_type: Optional[str] = None,
                           limit: int = 100, offset: int = 0) -> list[dict]:
        query = "SELECT * FROM entries WHERE job_id = ?"
        params: list = [job_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        if app_type:
            query += " AND app_type = ?"
            params.append(app_type)
        query += " ORDER BY entry_num ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor = await self._db.execute(query, params)
        rows = await cursor.fetchall()
        
        result = []
        for r in rows:
            d = dict(r)
            d.pop("embedding", None)
            result.append(d)
        return result

    async def update_entry(self, entry_id: str, **kwargs):
        sets = ["updated_at = ?"]
        vals = [datetime.utcnow().isoformat()]
        for k, v in kwargs.items():
            sets.append(f"{k} = ?")
            if isinstance(v, (dict, list)):
                vals.append(json.dumps(v))
            else:
                vals.append(v)
        vals.append(entry_id)
        await self._db.execute(
            f"UPDATE entries SET {', '.join(sets)} WHERE id = ?", vals
        )
        await self._db.commit()

    async def count_entries(self, job_id: str, status: Optional[str] = None) -> int:
        if status:
            cursor = await self._db.execute(
                "SELECT COUNT(*) FROM entries WHERE job_id = ? AND status = ?",
                (job_id, status),
            )
        else:
            cursor = await self._db.execute(
                "SELECT COUNT(*) FROM entries WHERE job_id = ?", (job_id,)
            )
        row = await cursor.fetchone()
        return row[0]

    # ── Checkpoint ────────────────────────────────────────

    async def get_checkpoint(self, job_id: str) -> Optional[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM checkpoints WHERE job_id = ?", (job_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def update_checkpoint(self, job_id: str, last_entry: int,
                                next_global_id: int, next_part: int):
        await self._db.execute(
            """UPDATE checkpoints
               SET last_entry = ?, next_global_id = ?, next_part = ?, updated_at = ?
               WHERE job_id = ?""",
            (last_entry, next_global_id, next_part,
             datetime.utcnow().isoformat(), job_id),
        )
        await self._db.commit()

    # ── Dedup Registry ────────────────────────────────────

    async def add_to_dedup(self, entry_id: str, full_name: str,
                           normalized_title: str, opening_trigram: str,
                           rel_topic_mood: str):
        await self._db.execute(
            """INSERT INTO dedup_registry
               (entry_id, full_name, normalized_title, opening_trigram, rel_topic_mood)
               VALUES (?, ?, ?, ?, ?)""",
            (entry_id, full_name, normalized_title, opening_trigram, rel_topic_mood),
        )
        await self._db.commit()

    async def check_name_exists(self, full_name: str) -> bool:
        cursor = await self._db.execute(
            "SELECT 1 FROM dedup_registry WHERE full_name = ? LIMIT 1",
            (full_name,),
        )
        return await cursor.fetchone() is not None

    async def check_title_exists(self, normalized_title: str) -> bool:
        cursor = await self._db.execute(
            "SELECT 1 FROM dedup_registry WHERE normalized_title = ? LIMIT 1",
            (normalized_title,),
        )
        return await cursor.fetchone() is not None

    async def check_trigram_exists(self, trigram: str) -> bool:
        cursor = await self._db.execute(
            "SELECT 1 FROM dedup_registry WHERE opening_trigram = ? LIMIT 1",
            (trigram,),
        )
        return await cursor.fetchone() is not None

    async def count_combo(self, rel_topic_mood: str) -> int:
        cursor = await self._db.execute(
            "SELECT COUNT(*) FROM dedup_registry WHERE rel_topic_mood = ?",
            (rel_topic_mood,),
        )
        row = await cursor.fetchone()
        return row[0]

    async def get_all_embeddings(self) -> list[bytes]:
        cursor = await self._db.execute(
            "SELECT embedding FROM entries WHERE embedding IS NOT NULL AND status = 'accepted'"
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

    async def get_recent_titles(self, limit: int = 50) -> list[str]:
        cursor = await self._db.execute(
            """SELECT normalized_title FROM dedup_registry
               WHERE normalized_title IS NOT NULL AND normalized_title != ''
               ORDER BY id DESC LIMIT ?""",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]
