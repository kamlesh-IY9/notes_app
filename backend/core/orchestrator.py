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
from .translator import translate_to_hindi
from .validator import validate_note, auto_fix_note
from .dedup import check_all_dedup, normalize_title, get_opening_trigram
from .jitter import apply_jitter
from .screenshot import render_screenshot, close_browser, MIUI_THEMES
from .contact_generator import generate_contact_note, validate_contact_note
from .event_generator import generate_event_note, validate_event_note
from .toi_generator import generate_toi_note, validate_toi_note

log = logging.getLogger(__name__)

# Filler openers used as a last-resort first-word replacement when the
# "never-reject" fallback accepts a note whose starting word is over-used.
_FILLER_STARTS = [
    "low key", "finally", "remind me", "so", "been thinking",
    "just realized", "cant believe", "wondering if", "maybe",
    "ok so", "btw", "thinking abt", "heads up", "almost forgot",
    "quick note", "got a", "told", "saw", "update on", "latest",
    "scheduled", "meant to", "apparently", "keep forgetting",
]


def _swap_first_word(note: str, banned: set[str]) -> str:
    """Replace the first word with a filler if it's in the banned set."""
    words = note.split()
    if not words:
        return note
    if words[0].lower() in banned:
        filler = random.choice([f for f in _FILLER_STARTS if f.split()[0].lower() not in banned])
        return filler + " " + " ".join(words[1:])
    return note


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
            int(os.getenv("MAX_LLM_CONCURRENCY", "15"))
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
        language = config.get("language", "english")

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
        default_min = "2026-04-27"
        default_max = "2026-04-30"
        date_min = datetime.fromisoformat(config.get("date_min", default_min))
        date_max = datetime.fromisoformat(config.get("date_max", default_max))
        conn_dist = config.get("connectivity_distribution", {
            "wifi_cellular": 60, "cellular_only": 25, "wifi_only": 10, "no_service": 5
        })

        start_entry = checkpoint["last_entry"]
        global_id = checkpoint["next_global_id"]
        part_num = checkpoint["next_part"]

        # Reset persona sampler for new job (switch language first if needed)
        self.persona_sampler.switch_language(language)
        self.persona_sampler.reset()
        # Per-job MIUI theme rotation iterator (Fisher-Yates shuffle, no consecutive duplicates).
        # Stored in _active_jobs so _save_entry can pull from it without parameter plumbing.
        self._active_jobs[job_id]["miui_theme_iter"] = _miui_theme_iterator()
        self._active_jobs[job_id]["used_contact_names"] = set()
        self._active_jobs[job_id]["used_contact_first_counts"] = {}  # first_name -> count (max 2)
        self._active_jobs[job_id]["starting_word_counts"] = {}  # word -> count

        # Pre-assign global_id and part_num for every entry so concurrent workers
        # get stable, non-colliding IDs without coordinating at runtime.
        entry_assignments = []
        cur_global_id = global_id
        cur_part_num = part_num
        for i in range(start_entry, batch_size):
            entry_num = i + 1
            entry_assignments.append((entry_num, cur_global_id, cur_part_num))
            cur_global_id += 1
            if entry_num % 20 == 0:
                cur_part_num += 1

        if dataset_type == "contacts":
            # Contacts are zero-LLM (pure templates) — already very fast; keep sequential.
            for entry_num, g_id, p_num in entry_assignments:
                ctrl = self._active_jobs.get(job_id, {})
                if ctrl.get("cancelled"):
                    await self.db.update_job_status(job_id, "cancelled")
                    yield {"event": "job_cancelled", "data": {"job_id": job_id}}
                    self._active_jobs.pop(job_id, None)
                    return

                while ctrl.get("paused"):
                    await asyncio.sleep(1)
                    ctrl = self._active_jobs.get(job_id, {})

                yield {"event": "entry_started", "data": {
                    "entry_num": entry_num, "global_id": g_id, "total": batch_size
                }}
                try:
                    result = await self._generate_contact_entry(
                        job_id=job_id, entry_num=entry_num, global_id=g_id, part_num=p_num,
                        config=config, app_dist=contact_app_dist,
                        date_min=date_min, date_max=date_max, conn_dist=conn_dist,
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
                        "entry_num": entry_num, "global_id": g_id, "error": str(e)
                    }}

                next_part = p_num + 1 if entry_num % 20 == 0 else p_num
                await self.db.update_checkpoint(job_id, entry_num, g_id + 1, next_part)

        elif dataset_type in ("events", "topics_of_interest"):
            # Events / TOI: concurrent LLM workers (same pattern as P&R)
            event_queue: asyncio.Queue = asyncio.Queue()
            worker_sem = asyncio.Semaphore(int(os.getenv("MAX_WORKER_CONCURRENCY", "8")))
            id_map = {en: (g_id, p_num) for en, g_id, p_num in entry_assignments}

            async def _run_llm_entry(entry_num: int, g_id: int, p_num: int) -> None:
                async with worker_sem:
                    ctrl = self._active_jobs.get(job_id, {})
                    if ctrl.get("cancelled"):
                        await event_queue.put(("entry_skipped", {"entry_num": entry_num}))
                        return
                    while ctrl.get("paused"):
                        await asyncio.sleep(1)
                        ctrl = self._active_jobs.get(job_id, {})

                    await event_queue.put(("entry_started", {
                        "entry_num": entry_num, "global_id": g_id, "total": batch_size
                    }))
                    try:
                        if dataset_type == "events":
                            result = await self._generate_events_entry(
                                job_id=job_id, entry_num=entry_num, global_id=g_id, part_num=p_num,
                                config=config, app_dist=app_dist,
                                date_min=date_min, date_max=date_max, conn_dist=conn_dist,
                            )
                        else:
                            result = await self._generate_toi_entry(
                                job_id=job_id, entry_num=entry_num, global_id=g_id, part_num=p_num,
                                config=config, app_dist=app_dist,
                                date_min=date_min, date_max=date_max, conn_dist=conn_dist,
                            )
                        await event_queue.put(("entry_completed", result))
                    except Exception as e:
                        log.error("Entry %d failed: %s", entry_num, e, exc_info=True)
                        await event_queue.put(("entry_failed", {
                            "entry_num": entry_num, "global_id": g_id, "error": str(e)
                        }))

            tasks = [
                asyncio.create_task(_run_llm_entry(en, g_id, p_num))
                for en, g_id, p_num in entry_assignments
            ]

            total = len(entry_assignments)
            done = 0
            job_cancel_emitted = False

            while done < total:
                event_type, data = await event_queue.get()

                if event_type == "entry_started":
                    yield {"event": "entry_started", "data": data}
                elif event_type == "entry_completed":
                    yield {"event": "entry_completed", "data": data}
                    await self.db.increment_job_counter(job_id, "generated")
                    if data["status"] == "accepted":
                        await self.db.increment_job_counter(job_id, "accepted")
                    else:
                        await self.db.increment_job_counter(job_id, "rejected")
                    en = data["entry_num"]
                    g_id, p_num = id_map[en]
                    next_part = p_num + 1 if en % 20 == 0 else p_num
                    await self.db.update_checkpoint(job_id, en, g_id + 1, next_part)
                    done += 1
                elif event_type == "entry_failed":
                    yield {"event": "entry_failed", "data": data}
                    await self.db.increment_job_counter(job_id, "failed")
                    done += 1
                elif event_type == "entry_skipped":
                    done += 1
                    if not job_cancel_emitted:
                        job_cancel_emitted = True
                        await self.db.update_job_status(job_id, "cancelled")
                        yield {"event": "job_cancelled", "data": {"job_id": job_id}}

            await asyncio.gather(*tasks, return_exceptions=True)

            if job_cancel_emitted:
                self._active_jobs.pop(job_id, None)
                return

        else:
            # P&R: run entries concurrently — each worker independently acquires the
            # LLM semaphore, so up to MAX_WORKER_CONCURRENCY entries are in flight at
            # once instead of one at a time. All quality logic inside
            # _generate_single_entry is untouched.
            event_queue: asyncio.Queue = asyncio.Queue()
            worker_sem = asyncio.Semaphore(int(os.getenv("MAX_WORKER_CONCURRENCY", "8")))
            id_map = {en: (g_id, p_num) for en, g_id, p_num in entry_assignments}

            async def _run_pr_entry(entry_num: int, g_id: int, p_num: int) -> None:
                async with worker_sem:
                    ctrl = self._active_jobs.get(job_id, {})
                    if ctrl.get("cancelled"):
                        await event_queue.put(("entry_skipped", {"entry_num": entry_num}))
                        return
                    while ctrl.get("paused"):
                        await asyncio.sleep(1)
                        ctrl = self._active_jobs.get(job_id, {})

                    await event_queue.put(("entry_started", {
                        "entry_num": entry_num, "global_id": g_id, "total": batch_size
                    }))
                    try:
                        result = await self._generate_single_entry(
                            job_id=job_id, entry_num=entry_num, global_id=g_id, part_num=p_num,
                            config=config, app_dist=app_dist, dark_share=dark_share,
                            title_share=title_share, date_min=date_min, date_max=date_max,
                            conn_dist=conn_dist,
                        )
                        await event_queue.put(("entry_completed", result))
                    except Exception as e:
                        log.error("Entry %d failed: %s", entry_num, e, exc_info=True)
                        await event_queue.put(("entry_failed", {
                            "entry_num": entry_num, "global_id": g_id, "error": str(e)
                        }))

            tasks = [
                asyncio.create_task(_run_pr_entry(en, g_id, p_num))
                for en, g_id, p_num in entry_assignments
            ]

            total = len(entry_assignments)
            done = 0
            job_cancel_emitted = False

            while done < total:
                event_type, data = await event_queue.get()

                if event_type == "entry_started":
                    yield {"event": "entry_started", "data": data}

                elif event_type == "entry_completed":
                    yield {"event": "entry_completed", "data": data}
                    await self.db.increment_job_counter(job_id, "generated")
                    if data["status"] == "accepted":
                        await self.db.increment_job_counter(job_id, "accepted")
                    else:
                        await self.db.increment_job_counter(job_id, "rejected")
                    en = data["entry_num"]
                    g_id, p_num = id_map[en]
                    next_part = p_num + 1 if en % 20 == 0 else p_num
                    await self.db.update_checkpoint(job_id, en, g_id + 1, next_part)
                    done += 1

                elif event_type == "entry_failed":
                    yield {"event": "entry_failed", "data": data}
                    await self.db.increment_job_counter(job_id, "failed")
                    done += 1

                elif event_type == "entry_skipped":
                    # Worker saw the cancel flag before starting — drain remaining.
                    done += 1
                    if not job_cancel_emitted:
                        job_cancel_emitted = True
                        await self.db.update_job_status(job_id, "cancelled")
                        yield {"event": "job_cancelled", "data": {"job_id": job_id}}

            await asyncio.gather(*tasks, return_exceptions=True)

            if job_cancel_emitted:
                self._active_jobs.pop(job_id, None)
                return

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
        max_retries = 10

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

                # Build banned starts list: any word already used >= 2 times
                sw_counts = self._active_jobs.get(job_id, {}).get("starting_word_counts", {})
                banned_starts = [w for w, c in sw_counts.items() if c >= 2]

                # Step 8: Generate note (Pass A — Groq/Llama)
                async with self._llm_semaphore:
                    note = await generate_note(
                        self.llm, persona, relationship, topic,
                        mood, related_name, has_title, style,
                        related_gender=related_gender,
                        banned_starts=banned_starts,
                        language=config.get("language", "english"),
                    )

                # Step 9: Humanize (Pass B — Gemini, ~75% of the time)
                async with self._llm_semaphore:
                    note = await humanize_note(self.llm, note, persona)

                # Step 9b: Pass C — translate to Hindi Devanagari (Hindi jobs only)
                note_text_en = None
                job_language = config.get("language", "english")
                if job_language == "hindi":
                    note_text_en = note  # preserve English source before translation
                    title_for_translate = note.split('\n')[0].strip() if has_title else None
                    note, _ = await translate_to_hindi(
                        note, title_for_translate, has_title
                    )

                # Step 10: Stylometric jitter
                note = apply_jitter(note, persona, style)

                # Step 11: Validate
                validation = validate_note(
                    note, persona, related_name, relationship, has_title,
                    note_date.isoformat(),
                )

                # Diversity Check: First word repetition (max 5).
                # IMPORTANT: count is incremented HERE (before any await) so concurrent
                # workers see the update immediately — not deferred to _save_entry.
                # This is safe in asyncio because the read-check-write below has no await,
                # so no other coroutine can interleave between the check and the increment.
                first_word = note.split()[0].lower() if note.split() else ""
                if first_word:
                    counts = self._active_jobs.get(job_id, {}).get("starting_word_counts", {})
                    if counts.get(first_word, 0) >= 5:
                        if attempt < max_retries - 1:
                            log.warning(f"Diversity check failed: word '{first_word}' repeats too much. Retrying.")
                            continue
                        else:
                            # Last resort: swap the first word rather than letting it repeat
                            note = _swap_first_word(note, set(w for w, c in counts.items() if c >= 5))
                            first_word = note.split()[0].lower() if note.split() else first_word
                    # Reserve this starting word now — visible to all concurrent workers immediately
                    counts[first_word] = counts.get(first_word, 0) + 1
                
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
                            return await self._save_entry(
                                job_id, entry_num, global_id, part_num,
                                note, persona, relationship, topic, mood,
                                related_name, has_title, note_date, style,
                                validation, config, app_dist, dark_share,
                                conn_dist, status="accepted", embedding=None,
                                note_text_en=note_text_en,
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
                        return await self._save_entry(
                            job_id, entry_num, global_id, part_num,
                            note, persona, relationship, topic, mood,
                            related_name, has_title, note_date, style,
                            validation, config, app_dist, dark_share,
                            conn_dist, status="accepted", embedding=embedding,
                            note_text_en=note_text_en,
                        )

                # All checks passed — save as accepted
                return await self._save_entry(
                    job_id, entry_num, global_id, part_num,
                    note, persona, relationship, topic, mood,
                    related_name, has_title, note_date, style,
                    validation, config, app_dist, dark_share,
                    conn_dist, status="accepted", embedding=embedding,
                    note_text_en=note_text_en,
                )

            except Exception as e:
                log.error("Generation attempt %d failed: %s", attempt + 1, e, exc_info=True)
                if attempt >= max_retries - 1:
                    raise
                # Exponential backoff for rate limits/API errors
                backoff_time = min(60, (2 ** attempt)) + random.uniform(1, 3)
                log.info(f"Sleeping {backoff_time:.2f}s before retry {attempt + 2} due to error...")
                await asyncio.sleep(backoff_time)

        raise RuntimeError(f"All {max_retries} retry attempts exhausted")

    async def _generate_contact_entry(
        self, job_id, entry_num, global_id, part_num,
        config, app_dist, date_min, date_max, conn_dist,
    ) -> dict:
        """Generate and save one contacts-mode entry."""
        max_retries = 10

        for attempt in range(max_retries):
            used_names = self._active_jobs.get(job_id, {}).get("used_contact_names", set())
            used_first_counts = self._active_jobs.get(job_id, {}).get("used_contact_first_counts", {})
            contact = generate_contact_note(used_names=used_names, used_first_counts=used_first_counts, language=config.get("language", "english"))
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

            # Diversity Check: First word repetition (max 5)
            first_word = note.split()[0].lower() if note.split() else ""
            if first_word:
                counts = self._active_jobs.get(job_id, {}).get("starting_word_counts", {})
                if counts.get(first_word, 0) >= 5:
                    if attempt < max_retries - 1:
                        log.warning(f"Contact Diversity check failed: word '{first_word}' repeats too much. Retrying.")
                        continue

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
            fname_lower = contact["contact_first_name"].lower()
            used_names.add(fname_lower)
            used_names.add(contact["contact_name"].lower())
            used_first_counts[fname_lower] = used_first_counts.get(fname_lower, 0) + 1

            # Pass C: translate contact note to Hindi if needed
            contact_note_en = None
            contact_language = config.get("language", "english")
            if contact_language == "hindi":
                contact_note_en = note
                note, _ = await translate_to_hindi(
                    note, None, False
                )

            return await self._save_contact_entry(
                job_id, entry_num, global_id, part_num,
                note, persona, contact, note_date, validation,
                app_dist, conn_dist, status="accepted",
                config=config, note_text_en=contact_note_en,
            )

        raise RuntimeError(f"All {max_retries} contact retry attempts exhausted")

    async def _save_entry(
        self, job_id, entry_num, global_id, part_num,
        note, persona, relationship, topic, mood,
        related_name, has_title, note_date, style,
        validation, config, app_dist, dark_share,
        conn_dist, status="accepted", embedding=None,
        note_text_en=None,
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
        job_language = config.get("language", "english")
        locale = "hi_IN" if job_language == "hindi" else "en_US"
        title_slug = _make_slug(title or (lines[0] if lines else "untitled"))
        txt_filename = f"{global_id}_{locale}_notes_people relationships___PART{part_num:03d}_{entry_num}.txt"
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
                    language=job_language,
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
            language=job_language,
            note_text_en=note_text_en,
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
        config=None, note_text_en=None,
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

        contact_language = (config or {}).get("language", "english")
        contact_locale = "hi_IN" if contact_language == "hindi" else "en_US"
        lines = note.split('\n')
        title = lines[0].strip() if lines else contact["contact_name"]
        title_slug = _make_slug(title)
        txt_filename = f"{global_id}_{contact_locale}_notes_contacts___PART{part_num:03d}_{entry_num}.txt"
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
                    language=contact_language,
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
            language=contact_language,
            note_text_en=note_text_en,
        )

        norm_title = normalize_title(title)
        body_lines = lines[1:] if len(lines) > 1 else lines
        trigram = get_opening_trigram(body_lines[0] if body_lines else title)
        combo = f"contacts|{contact['category']}|{contact['role']}"
        await self.db.add_to_dedup(entry_id, contact["contact_name"], norm_title, trigram, combo)
        
        # Update starting word counts for diversity tracking
        first_word = note.split()[0].lower() if note.split() else ""
        if first_word:
            counts = self._active_jobs.get(job_id, {}).get("starting_word_counts", {})
            counts[first_word] = counts.get(first_word, 0) + 1

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

    async def _generate_events_entry(
        self, job_id, entry_num, global_id, part_num,
        config, app_dist, date_min, date_max, conn_dist,
    ) -> dict:
        """Generate and save one event-mode entry (LLM-based)."""
        language = config.get("language", "english")
        max_retries = 10

        # Lightweight persona for context (age/occ/state only)
        persona = self.persona_sampler.sample_persona()

        for attempt in range(max_retries):
            async with self._llm_semaphore:
                note, meta = await generate_event_note(self.llm, persona, language)

            # Pass B: humanize (same as P&R — breaks AI fingerprint, ~70% of time)
            async with self._llm_semaphore:
                note = await humanize_note(self.llm, note, persona)

            failures = validate_event_note(note, language)
            if failures and attempt < max_retries - 1:
                log.warning("Event validation failed (attempt %d): %s", attempt + 1, failures)
                await self.db.increment_job_counter(job_id, "retried")
                continue
            if failures:
                log.warning("Accepting event after retries: %s", failures)

            # Pass C: translate to Hindi if needed
            note_en = None
            if language == "hindi":
                note_en = note
                note, _ = await translate_to_hindi(note, None, False)

            total_days = (date_max - date_min).days
            note_date = date_min + timedelta(days=random.randint(0, max(0, total_days)))
            note_date = note_date.replace(
                hour=random.randint(0, 23), minute=random.randint(0, 59)
            )

            return await self._save_events_entry(
                job_id, entry_num, global_id, part_num,
                note, persona, meta, note_date,
                failures, config, app_dist, conn_dist, note_en,
            )

        raise RuntimeError(f"All {max_retries} event retry attempts exhausted")

    async def _generate_toi_entry(
        self, job_id, entry_num, global_id, part_num,
        config, app_dist, date_min, date_max, conn_dist,
    ) -> dict:
        """Generate and save one TOI-mode entry (LLM-based)."""
        language = config.get("language", "english")
        max_retries = 10

        persona = self.persona_sampler.sample_persona()

        for attempt in range(max_retries):
            async with self._llm_semaphore:
                note, meta = await generate_toi_note(self.llm, persona, language)

            # Pass B: humanize (same as P&R — breaks AI fingerprint, ~70% of time)
            async with self._llm_semaphore:
                note = await humanize_note(self.llm, note, persona)

            failures = validate_toi_note(note, language)
            if failures and attempt < max_retries - 1:
                log.warning("TOI validation failed (attempt %d): %s", attempt + 1, failures)
                await self.db.increment_job_counter(job_id, "retried")
                continue
            if failures:
                log.warning("Accepting TOI after retries: %s", failures)

            note_en = None
            if language == "hindi":
                note_en = note
                note, _ = await translate_to_hindi(note, None, False)

            total_days = (date_max - date_min).days
            note_date = date_min + timedelta(days=random.randint(0, max(0, total_days)))
            note_date = note_date.replace(
                hour=random.randint(0, 23), minute=random.randint(0, 59)
            )

            return await self._save_toi_entry(
                job_id, entry_num, global_id, part_num,
                note, persona, meta, note_date,
                failures, config, app_dist, conn_dist, note_en,
            )

        raise RuntimeError(f"All {max_retries} TOI retry attempts exhausted")

    async def _save_events_entry(
        self, job_id, entry_num, global_id, part_num,
        note, persona, meta, note_date, failures,
        config, app_dist, conn_dist, note_text_en=None,
    ) -> dict:
        """Save an events-mode entry."""
        language = config.get("language", "english")
        locale = "hi_IN" if language == "hindi" else "en_US"

        app_types = list(app_dist.keys())
        app_type = random.choices(app_types, weights=[app_dist[a] for a in app_types], k=1)[0]
        if app_type == "miui_notes":
            theme_iter = self._active_jobs.get(job_id, {}).get("miui_theme_iter")
            theme = next(theme_iter) if theme_iter else random.choice(MIUI_THEMES)
        elif app_type == "apple_notes":
            theme = random.choice(["ios-paper light", "ios-warm light", "ios-creamy light", "ios-classic light", "dark", "light"])
        else:
            theme = "dark"

        conn_types = list(conn_dist.keys())
        connectivity = random.choices(conn_types, weights=[conn_dist[c] for c in conn_types], k=1)[0]

        lines = [l for l in note.split("\n") if l.strip()]
        has_title = len(lines) > 1
        title = lines[0].strip() if has_title else None
        title_slug = _make_slug(title or (lines[0] if lines else "event"))

        txt_filename = f"{global_id}_{locale}_notes_events___PART{part_num:03d}_{entry_num}.txt"
        jpg_filename = f"{global_id} {title_slug}.jpg"

        job_dir = Path(self.output_dir) / "jobs" / job_id
        notes_dir = job_dir / "notes"
        screenshots_dir = job_dir / "screenshots"
        notes_dir.mkdir(parents=True, exist_ok=True)
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        txt_path = str(notes_dir / txt_filename)
        jpg_path = str(screenshots_dir / jpg_filename)

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(note)
            if not note.endswith("\n"):
                f.write("\n")

        status = "accepted" if not failures else "rejected"
        if status == "accepted":
            async with self._pw_semaphore:
                await render_screenshot(
                    note_text=note, has_title=has_title, app_type=app_type,
                    theme=theme, note_date=note_date, connectivity=connectivity,
                    output_path=jpg_path, language=language,
                )

        persona_stored = {
            "full_name": persona.get("full_name", ""),
            "age": persona.get("age"),
            "gender": persona.get("gender", "unknown"),
            "state": persona.get("state", ""),
            "occupation": persona.get("occupation", ""),
            "dataset_type": "events",
            "event_type": meta.get("event_type", ""),
            "event_label": meta.get("event_label", ""),
        }

        entry_id = await self.db.create_entry(
            job_id=job_id, entry_num=entry_num, global_id=global_id, part_num=part_num,
            status=status, persona_json=json.dumps(persona_stored),
            note_text=note, has_title=1 if has_title else 0, title=title,
            app_type=app_type, theme=theme, connectivity=connectivity,
            note_date=note_date.isoformat(),
            relationship="event", topic=meta.get("event_type", "event"),
            mood="neutral",
            word_count=len(note.split()),
            line_count=len(lines),
            txt_filename=txt_filename, jpg_filename=jpg_filename,
            txt_path=txt_path, jpg_path=jpg_path,
            validation_json=json.dumps({"checks": failures, "passed": not failures}),
            embedding=None, language=language, note_text_en=note_text_en,
        )

        norm_title = normalize_title(title or (lines[0] if lines else "event"))
        trigram = get_opening_trigram(lines[1] if len(lines) > 1 else (lines[0] if lines else ""))
        await self.db.add_to_dedup(entry_id, title or "", norm_title, trigram, f"events|{meta.get('event_type', '')}")

        log.info("Event entry %d (ID %d) %s — %s/%s, %s", entry_num, global_id, status, app_type, theme, meta.get("event_label", ""))

        return {
            "entry_id": entry_id, "entry_num": entry_num, "global_id": global_id,
            "status": status, "app_type": app_type, "theme": theme,
            "has_title": has_title, "title": title,
            "persona_summary": f"{persona.get('age', '?')}{str(persona.get('gender', 'u'))[0].upper()}, {persona.get('occupation', '')}, {persona.get('state', '')}",
            "word_count": len(note.split()),
            "txt_filename": txt_filename, "jpg_filename": jpg_filename,
        }

    async def _save_toi_entry(
        self, job_id, entry_num, global_id, part_num,
        note, persona, meta, note_date, failures,
        config, app_dist, conn_dist, note_text_en=None,
    ) -> dict:
        """Save a topics-of-interest entry."""
        language = config.get("language", "english")
        locale = "hi_IN" if language == "hindi" else "en_US"

        app_types = list(app_dist.keys())
        app_type = random.choices(app_types, weights=[app_dist[a] for a in app_types], k=1)[0]
        if app_type == "miui_notes":
            theme_iter = self._active_jobs.get(job_id, {}).get("miui_theme_iter")
            theme = next(theme_iter) if theme_iter else random.choice(MIUI_THEMES)
        elif app_type == "apple_notes":
            theme = random.choice(["ios-paper light", "ios-warm light", "ios-creamy light", "ios-classic light", "dark", "light"])
        else:
            theme = "dark"

        conn_types = list(conn_dist.keys())
        connectivity = random.choices(conn_types, weights=[conn_dist[c] for c in conn_types], k=1)[0]

        lines = [l for l in note.split("\n") if l.strip()]
        has_title = True  # TOI always has a title (the topic name)
        title = lines[0].strip() if lines else meta.get("topic_name", "topic")
        title_slug = _make_slug(title)

        txt_filename = f"{global_id}_{locale}_notes_topics___PART{part_num:03d}_{entry_num}.txt"
        jpg_filename = f"{global_id} {title_slug}.jpg"

        job_dir = Path(self.output_dir) / "jobs" / job_id
        notes_dir = job_dir / "notes"
        screenshots_dir = job_dir / "screenshots"
        notes_dir.mkdir(parents=True, exist_ok=True)
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        txt_path = str(notes_dir / txt_filename)
        jpg_path = str(screenshots_dir / jpg_filename)

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(note)
            if not note.endswith("\n"):
                f.write("\n")

        status = "accepted" if not failures else "rejected"
        if status == "accepted":
            async with self._pw_semaphore:
                await render_screenshot(
                    note_text=note, has_title=has_title, app_type=app_type,
                    theme=theme, note_date=note_date, connectivity=connectivity,
                    output_path=jpg_path, language=language,
                )

        persona_stored = {
            "full_name": persona.get("full_name", ""),
            "age": persona.get("age"),
            "gender": persona.get("gender", "unknown"),
            "state": persona.get("state", ""),
            "occupation": persona.get("occupation", ""),
            "dataset_type": "topics_of_interest",
            "topic_name": meta.get("topic_name", ""),
            "category": meta.get("category", ""),
        }

        entry_id = await self.db.create_entry(
            job_id=job_id, entry_num=entry_num, global_id=global_id, part_num=part_num,
            status=status, persona_json=json.dumps(persona_stored),
            note_text=note, has_title=1, title=title,
            app_type=app_type, theme=theme, connectivity=connectivity,
            note_date=note_date.isoformat(),
            relationship="toi", topic=meta.get("category", "topic"),
            mood="focused",
            word_count=len(note.split()),
            line_count=len(lines),
            txt_filename=txt_filename, jpg_filename=jpg_filename,
            txt_path=txt_path, jpg_path=jpg_path,
            validation_json=json.dumps({"checks": failures, "passed": not failures}),
            embedding=None, language=language, note_text_en=note_text_en,
        )

        norm_title = normalize_title(title)
        body_lines = lines[1:] if len(lines) > 1 else lines
        trigram = get_opening_trigram(body_lines[0] if body_lines else title)
        await self.db.add_to_dedup(entry_id, title, norm_title, trigram, f"toi|{meta.get('category', '')}")

        log.info("TOI entry %d (ID %d) %s — %s/%s, %s", entry_num, global_id, status, app_type, theme, meta.get("topic_name", ""))

        return {
            "entry_id": entry_id, "entry_num": entry_num, "global_id": global_id,
            "status": status, "app_type": app_type, "theme": theme,
            "has_title": True, "title": title,
            "persona_summary": f"{persona.get('age', '?')}{str(persona.get('gender', 'u'))[0].upper()}, {persona.get('occupation', '')}, {persona.get('state', '')}",
            "word_count": len(note.split()),
            "txt_filename": txt_filename, "jpg_filename": jpg_filename,
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
