"""Orchestrator — drives the per-entry 17-step generation pipeline."""

import asyncio
import json
import logging
import os
import random
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import AsyncGenerator, Optional

import numpy as np

from .llm_clients import LLMClients
from .persona import PersonaSampler
from .note_generator import generate_note, sample_style
from .humanizer import humanize_note
from .validator import validate_note, auto_fix_note
from .dedup import check_all_dedup, normalize_title, get_opening_trigram
from .jitter import apply_jitter
from .screenshot import render_screenshot, close_browser, MIUI_THEMES
from .contact_generator import generate_contact_note, validate_contact_note

log = logging.getLogger(__name__)


def _miui_theme_iterator():
    """Yield MIUI themes in Fisher-Yates shuffled chunks; never 2 consecutive same theme.

    Across a 200-batch this guarantees every theme is used at least 5–6 times and no
    theme is ever picked twice in a row (re-shuffles the next chunk if its head would
    repeat the previous chunk's tail).
    """
    last = None
    while True:
        chunk = list(MIUI_THEMES)
        random.shuffle(chunk)
        # Avoid the boundary where last theme of prior chunk equals first of new chunk.
        if last is not None and chunk and chunk[0] == last:
            # Swap with another position in the chunk to break the duplicate.
            swap_idx = random.randint(1, len(chunk) - 1) if len(chunk) > 1 else 0
            chunk[0], chunk[swap_idx] = chunk[swap_idx], chunk[0]
        for t in chunk:
            yield t
            last = t


class JobOrchestrator:
    """Orchestrates batch note generation jobs."""

    def __init__(self, db, llm_clients: LLMClients, output_dir: str):
        self.db = db
        self.llm = llm_clients
        self.output_dir = output_dir
        self.persona_sampler = PersonaSampler()
        self._active_jobs: dict[str, dict] = {}  # job_id -> control state
        self._llm_semaphore = asyncio.Semaphore(
            int(os.getenv("MAX_LLM_CONCURRENCY", "4"))
        )
        self._pw_semaphore = asyncio.Semaphore(
            int(os.getenv("MAX_PLAYWRIGHT_CONCURRENCY", "2"))
        )

    async def start_job(self, job_id: str) -> AsyncGenerator[dict, None]:
        """Start a generation job and yield SSE events."""
        job = await self.db.get_job(job_id)
        if not job:
            yield {"event": "error", "data": {"message": "Job not found"}}
            return

        config = json.loads(job["config"])
        batch_size = job["batch_size"]
        checkpoint = await self.db.get_checkpoint(job_id)
        dataset_type = config.get("dataset_type", "people_relationships")

        # Control state
        self._active_jobs[job_id] = {"paused": False, "cancelled": False}

        await self.db.update_job_status(job_id, "running")
        yield {"event": "job_started", "data": {"job_id": job_id, "batch_size": batch_size}}

        # Config params — shared across dataset modes.
        app_dist = config.get("app_distribution", {
            "apple_notes": 75, "miui_notes": 10, "samsung_notes": 10, "google_keep": 5
        })
        contact_app_dist = config.get("contact_app_distribution", {
            "miui_notes": 50,
            "apple_notes": 30,
            "samsung_notes": 12,
            "google_keep": 8,
        })
        dark_share = config.get("dark_mode_share", 25)  # only used by legacy templates
        title_share = config.get("title_share", 39)  # ~40% real titles randomly, rest empty placeholder
        # Default date range: shuffle between Apr 24, 25, 26 (2026). User can override
        # via the Generate form date pickers; whatever the form sends wins.
        default_min = "2026-04-24"
        default_max = "2026-04-26"
        date_min = datetime.fromisoformat(config.get("date_min", default_min))
        date_max = datetime.fromisoformat(config.get("date_max", default_max))
        conn_dist = config.get("connectivity_distribution", {
            "wifi_cellular": 60, "cellular_only": 25, "wifi_only": 10, "no_service": 5
        })

        start_entry = checkpoint["last_entry"]
        global_id = checkpoint["next_global_id"]
        part_num = checkpoint["next_part"]

        # Reset persona sampler for new job
        self.persona_sampler.reset()
        # Per-job MIUI theme rotation iterator (Fisher-Yates shuffle, no consecutive duplicates).
        # Stored in _active_jobs so _save_entry can pull from it without parameter plumbing.
        self._active_jobs[job_id]["miui_theme_iter"] = _miui_theme_iterator()
        self._active_jobs[job_id]["used_contact_names"] = set()

        for i in range(start_entry, batch_size):
            # Check control state
            ctrl = self._active_jobs.get(job_id, {})
            if ctrl.get("cancelled"):
                await self.db.update_job_status(job_id, "cancelled")
                yield {"event": "job_cancelled", "data": {"job_id": job_id}}
                break

            while ctrl.get("paused"):
                await asyncio.sleep(1)
                ctrl = self._active_jobs.get(job_id, {})

            entry_num = i + 1
            yield {"event": "entry_started", "data": {
                "entry_num": entry_num, "global_id": global_id, "total": batch_size
            }}

            try:
                if dataset_type == "contacts":
                    result = await self._generate_contact_entry(
                        job_id=job_id,
                        entry_num=entry_num,
                        global_id=global_id,
                        part_num=part_num,
                        config=config,
                        app_dist=contact_app_dist,
                        date_min=date_min,
                        date_max=date_max,
                        conn_dist=conn_dist,
                    )
                else:
                    result = await self._generate_single_entry(
                        job_id=job_id,
                        entry_num=entry_num,
                        global_id=global_id,
                        part_num=part_num,
                        config=config,
                        app_dist=app_dist,
                        dark_share=dark_share,
                        title_share=title_share,
                        date_min=date_min,
                        date_max=date_max,
                        conn_dist=conn_dist,
                    )

                yield {"event": "entry_completed", "data": result}
                await self.db.increment_job_counter(job_id, "generated")
                if result["status"] == "accepted":
                    await self.db.increment_job_counter(job_id, "accepted")
                else:
                    await self.db.increment_job_counter(job_id, "rejected")

            except Exception as e:
                log.error("Entry %d failed: %s", entry_num, e, exc_info=True)
                await self.db.increment_job_counter(job_id, "failed")
                yield {"event": "entry_failed", "data": {
                    "entry_num": entry_num, "global_id": global_id, "error": str(e)
                }}

            # Update checkpoint
            global_id += 1
            entries_per_part = max(1, batch_size // max(1, (batch_size // 20)))
            if entry_num % 20 == 0:
                part_num += 1
            await self.db.update_checkpoint(job_id, entry_num, global_id, part_num)

        # Finalize
        if not self._active_jobs.get(job_id, {}).get("cancelled"):
            await self.db.update_job_status(job_id, "completed")
            yield {"event": "job_completed", "data": {"job_id": job_id}}

        # Cleanup
        self._active_jobs.pop(job_id, None)

    async def _generate_single_entry(
        self, job_id, entry_num, global_id, part_num,
        config, app_dist, dark_share, title_share,
        date_min, date_max, conn_dist,
    ) -> dict:
        """Execute the 17-step pipeline for a single entry."""
        max_retries = 5

        for attempt in range(max_retries):
            try:
                # Step 1: ID already assigned

                # Step 2: Sample persona
                persona = self.persona_sampler.sample_persona()

                # Step 3: Sample relationship, topic, mood
                relationship = self.persona_sampler.sample_relationship()
                topic = self.persona_sampler.sample_topic()
                mood = self.persona_sampler.sample_mood()

                # Step 4: Sample related name (gender-correct)
                related_name, related_gender = self.persona_sampler.sample_related_name(persona, relationship)

                # Step 5: Title decision
                has_title = random.random() < (title_share / 100)

                # Step 6: Sample date
                total_days = (date_max - date_min).days
                random_days = random.randint(0, max(0, total_days))
                note_date = date_min + timedelta(days=random_days)
                note_date = note_date.replace(
                    hour=random.randint(0, 23),
                    minute=random.randint(0, 59),
                )

                # Step 7: Sample style
                style = sample_style()
                if not has_title:
                    style["line_count"] = max(2, style["line_count"] - 1)

                # Step 8: Generate note (Pass A — Groq/Llama)
                async with self._llm_semaphore:
                    note = await generate_note(
                        self.llm, persona, relationship, topic,
                        mood, related_name, has_title, style,
                        related_gender=related_gender,
                    )

                # Step 9: Humanize (Pass B — Gemini, ~75% of the time)
                async with self._llm_semaphore:
                    note = await humanize_note(self.llm, note, persona)

                # Step 10: Stylometric jitter
                note = apply_jitter(note, persona, style)

                # Step 11: Validate
                validation = validate_note(
                    note, persona, related_name, relationship, has_title,
                    note_date.isoformat(),
                )

                if not validation.passed:
                    # Try auto-fix first
                    fixed_note, fixes = auto_fix_note(note)
                    if fixes:
                        note = fixed_note
                        validation = validate_note(
                            note, persona, related_name, relationship,
                            has_title, note_date.isoformat(),
                        )

                    if not validation.passed:
                        if attempt < max_retries - 1:
                            log.warning("Validation failed (attempt %d): %s",
                                       attempt + 1,
                                       [c for c in validation.checks if not c["passed"]])
                            await self.db.increment_job_counter(job_id, "retried")
                            continue
                        else:
                            # User requested NEVER to reject notes. We still try to follow rules (via retries),
                            # but if we run out of retries, we accept it anyway.
                            return await self._save_entry(
                                job_id, entry_num, global_id, part_num,
                                note, persona, relationship, topic, mood,
                                related_name, has_title, note_date, style,
                                validation, config, app_dist, dark_share,
                                conn_dist, status="accepted", embedding=None,
                            )

                # Step 12: Dedup check
                title_text = note.split('\n')[0] if has_title else None
                dedup_ok, dedup_reason, embedding = await check_all_dedup(
                    self.db, note, persona["full_name"], title_text,
                    has_title, relationship["id"], topic["id"], mood,
                )

                if not dedup_ok:
                    if attempt < max_retries - 1:
                        log.warning("Dedup failed (attempt %d): %s", attempt + 1, dedup_reason)
                        await self.db.increment_job_counter(job_id, "retried")
                        continue
                    else:
                        # Accept anyway if we run out of retries
                        return await self._save_entry(
                            job_id, entry_num, global_id, part_num,
                            note, persona, relationship, topic, mood,
                            related_name, has_title, note_date, style,
                            validation, config, app_dist, dark_share,
                            conn_dist, status="accepted", embedding=embedding,
                        )

                # All checks passed — save as accepted
                return await self._save_entry(
                    job_id, entry_num, global_id, part_num,
                    note, persona, relationship, topic, mood,
                    related_name, has_title, note_date, style,
                    validation, config, app_dist, dark_share,
                    conn_dist, status="accepted", embedding=embedding,
                )

            except Exception as e:
                log.error("Generation attempt %d failed: %s", attempt + 1, e, exc_info=True)
                if attempt >= max_retries - 1:
                    raise

        raise RuntimeError(f"All {max_retries} retry attempts exhausted")

    async def _generate_contact_entry(
        self, job_id, entry_num, global_id, part_num,
        config, app_dist, date_min, date_max, conn_dist,
    ) -> dict:
        """Generate and save one contacts-mode entry."""
        max_retries = 5

        for attempt in range(max_retries):
            used_names = self._active_jobs.get(job_id, {}).get("used_contact_names", set())
            contact = generate_contact_note(used_names=used_names)
            note = contact["note"]

            persona = {
                "full_name": contact["contact_name"],
                "first_name": contact["contact_name"].split()[0],
                "age": None,
                "age_bracket": None,
                "gender": "unknown",
                "state": "US",
                "occupation": contact["role"],
                "ethnicity": None,
                "voice_quirks": [],
                "dataset_type": "contacts",
            }
            note = apply_jitter(note, persona, style={})
            contact["note"] = note

            validation = validate_contact_note(note)

            if not validation.passed:
                if attempt < max_retries - 1:
                    log.warning(
                        "Contact validation failed (attempt %d): %s",
                        attempt + 1,
                        [c for c in validation.checks if not c["passed"]],
                    )
                    await self.db.increment_job_counter(job_id, "retried")
                    continue
                log.warning("Accepting contact after retries: %s", validation.to_dict())

            total_days = (date_max - date_min).days
            random_days = random.randint(0, max(0, total_days))
            note_date = date_min + timedelta(days=random_days)
            note_date = note_date.replace(
                hour=random.randint(0, 23),
                minute=random.randint(0, 59),
            )
            used_names.add(contact["contact_first_name"].lower())
            used_names.add(contact["contact_name"].lower())
            return await self._save_contact_entry(
                job_id, entry_num, global_id, part_num,
                note, persona, contact, note_date, validation,
                app_dist, conn_dist, status="accepted",
            )

        raise RuntimeError(f"All {max_retries} contact retry attempts exhausted")

    async def _save_entry(
        self, job_id, entry_num, global_id, part_num,
        note, persona, relationship, topic, mood,
        related_name, has_title, note_date, style,
        validation, config, app_dist, dark_share,
        conn_dist, status="accepted", embedding=None,
    ) -> dict:
        """Save entry files and database record."""

        # Choose app type
        app_types = list(app_dist.keys())
        app_weights = [app_dist[a] for a in app_types]
        app_type = random.choices(app_types, weights=app_weights, k=1)[0]

        # Choose theme: for MIUI, pull from the per-job Fisher-Yates iterator
        # (no consecutive duplicates, every theme used ~equally across the batch).
        if app_type == "miui_notes":
            theme_iter = self._active_jobs.get(job_id, {}).get("miui_theme_iter")
            theme = next(theme_iter) if theme_iter is not None else random.choice(MIUI_THEMES)
        elif app_type == "apple_notes":
            theme = random.choice(["ios-paper light", "ios-warm light", "ios-creamy light", "ios-classic light", "dark", "light"])
        else:
            theme = "dark"

        # Choose connectivity
        conn_types = list(conn_dist.keys())
        conn_weights = [conn_dist[c] for c in conn_types]
        connectivity = random.choices(conn_types, weights=conn_weights, k=1)[0]

        # Extract title
        lines = note.split('\n')
        title = lines[0].strip() if has_title and lines else None

        # Step 13: Build filenames
        title_slug = _make_slug(title or (lines[0] if lines else "untitled"))
        txt_filename = f"{global_id}_en_US_notes_people relationships___PART{part_num:03d}_{entry_num}.txt"
        jpg_filename = f"{global_id} {title_slug}.jpg"

        # Step 14: Write .txt
        job_dir = Path(self.output_dir) / "jobs" / job_id
        notes_dir = job_dir / "notes"
        screenshots_dir = job_dir / "screenshots"
        notes_dir.mkdir(parents=True, exist_ok=True)
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        txt_path = str(notes_dir / txt_filename)
        jpg_path = str(screenshots_dir / jpg_filename)

        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(note)
            if not note.endswith('\n'):
                f.write('\n')

        # Step 15: Render screenshot
        if status == "accepted":
            async with self._pw_semaphore:
                await render_screenshot(
                    note_text=note,
                    has_title=has_title,
                    app_type=app_type,
                    theme=theme,
                    note_date=note_date,
                    connectivity=connectivity,
                    output_path=jpg_path,
                )

        # Step 16: Save to DB
        embedding_bytes = embedding.tobytes() if embedding is not None else None

        entry_id = await self.db.create_entry(
            job_id=job_id,
            entry_num=entry_num,
            global_id=global_id,
            part_num=part_num,
            status=status,
            persona_json=json.dumps(persona),
            note_text=note,
            has_title=1 if has_title else 0,
            title=title,
            app_type=app_type,
            theme=theme,
            connectivity=connectivity,
            note_date=note_date.isoformat(),
            relationship=relationship["id"],
            topic=topic["id"],
            mood=mood,
            word_count=len(note.split()),
            line_count=len([l for l in note.split('\n') if l.strip()]),
            txt_filename=txt_filename,
            jpg_filename=jpg_filename,
            txt_path=txt_path,
            jpg_path=jpg_path,
            validation_json=json.dumps(validation.to_dict()),
            embedding=embedding_bytes,
        )

        # Add to dedup registry
        if status == "accepted":
            norm_title = normalize_title(title) if has_title else normalize_title(
                lines[1] if len(lines) > 1 and has_title else (lines[0] if lines else "")
            )
            body_lines = lines[1:] if has_title else lines
            trigram = get_opening_trigram(body_lines[0] if body_lines else "")
            combo = f"{relationship['id']}|{topic['id']}|{mood}"
            await self.db.add_to_dedup(
                entry_id, persona["full_name"], norm_title, trigram, combo
            )

        log.info(
            "Entry %d (ID %d) %s — %s/%s/%s, %s, %s",
            entry_num, global_id, status, app_type, theme, connectivity,
            f"title='{title}'" if has_title else "no-title",
            f"{len(note.split())}w/{len([l for l in note.split(chr(10)) if l.strip()])}l"
        )

        return {
            "entry_id": entry_id,
            "entry_num": entry_num,
            "global_id": global_id,
            "status": status,
            "app_type": app_type,
            "theme": theme,
            "has_title": has_title,
            "title": title,
            "persona_summary": f"{persona['age']}{persona['gender'][0].upper()}, {persona['occupation']}, {persona['state']}",
            "word_count": len(note.split()),
            "txt_filename": txt_filename,
            "jpg_filename": jpg_filename,
        }

    async def _save_contact_entry(
        self, job_id, entry_num, global_id, part_num,
        note, persona, contact, note_date, validation,
        app_dist, conn_dist, status="accepted",
    ) -> dict:
        """Save a contacts-mode entry with contact-specific filenames/metadata."""
        app_types = list(app_dist.keys())
        app_weights = [app_dist[a] for a in app_types]
        app_type = random.choices(app_types, weights=app_weights, k=1)[0]

        if app_type == "miui_notes":
            theme_iter = self._active_jobs.get(job_id, {}).get("miui_theme_iter")
            theme = next(theme_iter) if theme_iter is not None else random.choice(MIUI_THEMES)
        elif app_type == "apple_notes":
            theme = random.choice(["ios-paper light", "ios-warm light", "ios-creamy light", "ios-classic light", "dark", "light"])
        else:
            theme = "dark"

        conn_types = list(conn_dist.keys())
        conn_weights = [conn_dist[c] for c in conn_types]
        connectivity = random.choices(conn_types, weights=conn_weights, k=1)[0]

        lines = note.split('\n')
        title = lines[0].strip() if lines else contact["contact_name"]
        title_slug = _make_slug(title)
        txt_filename = f"{global_id}_en_US_notes_contacts___PART{part_num:03d}_{entry_num}.txt"
        jpg_filename = f"{global_id} {title_slug}.jpg"

        job_dir = Path(self.output_dir) / "jobs" / job_id
        notes_dir = job_dir / "notes"
        screenshots_dir = job_dir / "screenshots"
        notes_dir.mkdir(parents=True, exist_ok=True)
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        txt_path = str(notes_dir / txt_filename)
        jpg_path = str(screenshots_dir / jpg_filename)

        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(note)
            if not note.endswith('\n'):
                f.write('\n')

        # Randomize contact title chance to ~27%
        contact_has_title = random.random() < random.uniform(0.25, 0.30)

        if status == "accepted":
            async with self._pw_semaphore:
                await render_screenshot(
                    note_text=note,
                    has_title=contact_has_title,
                    app_type=app_type,
                    theme=theme,
                    note_date=note_date,
                    connectivity=connectivity,
                    output_path=jpg_path,
                )

        entry_id = await self.db.create_entry(
            job_id=job_id,
            entry_num=entry_num,
            global_id=global_id,
            part_num=part_num,
            status=status,
            persona_json=json.dumps(persona),
            note_text=note,
            has_title=1 if contact_has_title else 0,
            title=title,
            app_type=app_type,
            theme=theme,
            connectivity=connectivity,
            note_date=note_date.isoformat(),
            relationship="contact",
            topic=contact["category"],
            mood="practical",
            word_count=len(note.split()),
            line_count=len([l for l in note.split('\n') if l.strip()]),
            txt_filename=txt_filename,
            jpg_filename=jpg_filename,
            txt_path=txt_path,
            jpg_path=jpg_path,
            validation_json=json.dumps(validation.to_dict()),
            embedding=None,
        )

        norm_title = normalize_title(title)
        body_lines = lines[1:] if len(lines) > 1 else lines
        trigram = get_opening_trigram(body_lines[0] if body_lines else title)
        combo = f"contacts|{contact['category']}|{contact['role']}"
        await self.db.add_to_dedup(entry_id, contact["contact_name"], norm_title, trigram, combo)

        log.info(
            "Contact entry %d (ID %d) %s — %s/%s/%s, %s",
            entry_num, global_id, status, app_type, theme, connectivity, title,
        )

        return {
            "entry_id": entry_id,
            "entry_num": entry_num,
            "global_id": global_id,
            "status": status,
            "app_type": app_type,
            "theme": theme,
            "has_title": contact_has_title,
            "title": title,
            "persona_summary": f"Contact, {contact['role']}",
            "word_count": len(note.split()),
            "txt_filename": txt_filename,
            "jpg_filename": jpg_filename,
        }

    def pause_job(self, job_id: str):
        if job_id in self._active_jobs:
            self._active_jobs[job_id]["paused"] = True

    def resume_job(self, job_id: str):
        if job_id in self._active_jobs:
            self._active_jobs[job_id]["paused"] = False

    def cancel_job(self, job_id: str):
        if job_id in self._active_jobs:
            self._active_jobs[job_id]["cancelled"] = True


def _make_slug(text: str, max_len: int = 40) -> str:
    """Make a filename-safe slug from text."""
    slug = re.sub(r'[^\w\s-]', '', text)
    slug = slug.strip()[:max_len]
    return slug or "untitled"
