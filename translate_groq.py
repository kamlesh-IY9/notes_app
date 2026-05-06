"""
translate_groq.py — Translate missing English .txt files to Hindi Devanagari
using Groq (Llama-3.3-70B), then re-render .jpg screenshots.

Usage:
  python3 translate_groq.py
"""

import asyncio
import logging
import os
import re
import sqlite3
import random
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from openai import AsyncOpenAI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL  = "https://api.groq.com/openai/v1"
GROQ_MODEL     = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
DB_PATH        = "output/app.sqlite"

JOBS = [
    {
        "source": "output/sample - hindi - p_r notes/d296c257f0d0 - hindi - p-r/notes",
        "output": "output/translated-hindi-p_r",
    },
    {
        "source": "output/sample hindi - contacts notes/a8cd6a175de0 - contact - notes/notes",
        "output": "output/translated-hindi-contacts",
    },
]

SYSTEM_PROMPT = """You are a Hindi translator. Translate the English phone note to natural, casual, informal Hindi Devanagari.

RULES:
- Output ONLY Hindi Devanagari script
- Keep every line break exactly as-is — do NOT merge lines
- Keep proper names (people, places, brands) in English/Roman
- Keep numbers, phone numbers, dates, email addresses as-is
- Keep English abbreviations like ok, lol, idk, rn, tbh, bc, ngl, btw, tmrw, wknd, est — Indians use them
- Do NOT add formality — casual everyday Hindi
- Output ONLY the translated text, nothing else"""


def _has_devanagari(text: str) -> bool:
    return bool(re.search(r"[ऀ-ॿ]", text))


async def translate(client: AsyncOpenAI, text: str) -> str:
    lines = [l for l in text.split("\n") if l.strip()]
    n = len(lines)
    prompt = (
        f"Translate this {n}-line phone note to Hindi Devanagari. "
        f"Keep exactly {n} lines:\n\n{text}\n\n"
        f"Output ONLY the translated note. Keep {n} lines."
    )
    for attempt in range(3):
        try:
            resp = await asyncio.wait_for(
                client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user",   "content": prompt},
                    ],
                    temperature=0.2,
                    max_tokens=600,
                ),
                timeout=30.0,
            )
            result = resp.choices[0].message.content.strip().strip('"').strip("'")
            if result.startswith("```"):
                parts = result.split("```")
                result = parts[1].strip() if len(parts) > 1 else parts[0][3:].strip()
            if _has_devanagari(result):
                return result
            log.warning("Attempt %d — no Devanagari, retrying", attempt + 1)
        except asyncio.TimeoutError:
            log.warning("Attempt %d — timeout", attempt + 1)
        except Exception as e:
            log.warning("Attempt %d — %s", attempt + 1, e)
            if "rate" in str(e).lower():
                await asyncio.sleep(2)
    log.error("All attempts failed — keeping original")
    return text


def _db_metadata(global_id: int, entry_num: int) -> dict | None:
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT app_type, theme, has_title, note_date, connectivity "
            "FROM entries WHERE global_id=? AND entry_num=? LIMIT 1",
            (global_id, entry_num),
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def _random_metadata() -> dict:
    from backend.core.screenshot import MIUI_THEMES
    app = random.choices(
        ["miui_notes", "apple_notes", "samsung_notes", "google_keep"],
        weights=[40, 30, 20, 10], k=1
    )[0]
    theme = random.choice(MIUI_THEMES) if app == "miui_notes" else random.choice(["light", "dark"])
    return {
        "app_type": app,
        "theme": theme,
        "has_title": random.random() < 0.1,
        "note_date": datetime.now().isoformat(),
        "connectivity": random.choice(["wifi_cellular", "cellular_only", "wifi_only"]),
    }


async def process_file(
    client: AsyncOpenAI,
    txt_path: Path,
    out_dir: Path,
    sem: asyncio.Semaphore,
    idx: int,
    total: int,
):
    async with sem:
        log.info("[%d/%d] %s", idx, total, txt_path.name)

        english = txt_path.read_text(encoding="utf-8").strip()
        if not english:
            log.warning("Empty — skipping %s", txt_path.name)
            return

        # If already mostly Devanagari, skip translation
        if _has_devanagari(english) and len(re.findall(r"[ऀ-ॿ]", english)) > 10:
            hindi = english
            log.info("  → already Hindi, keeping as-is")
        else:
            hindi = await translate(client, english)

        out_txt = out_dir / txt_path.name
        out_txt.write_text(hindi, encoding="utf-8")

        m = re.match(r"^(\d+)_.*?_(\d+)\.txt$", txt_path.name)
        global_id = int(m.group(1)) if m else 0
        entry_num = int(m.group(2)) if m else 0
        meta = _db_metadata(global_id, entry_num) or _random_metadata()

        app_type     = meta["app_type"]
        theme        = meta["theme"]
        has_title    = bool(meta["has_title"])
        connectivity = meta.get("connectivity", "wifi_cellular")
        try:
            note_date = datetime.fromisoformat(meta["note_date"])
        except Exception:
            note_date = datetime.now()

        out_jpg = out_dir / (txt_path.stem + ".jpg")

        from backend.core.screenshot import render_screenshot
        try:
            await render_screenshot(
                note_text=hindi,
                has_title=has_title,
                app_type=app_type,
                theme=theme,
                note_date=note_date,
                connectivity=connectivity,
                output_path=str(out_jpg),
                language="hindi",
            )
        except Exception as e:
            log.error("Screenshot failed for %s: %s", txt_path.name, e)

        log.info("  → saved %s + %s", out_txt.name, out_jpg.name)


async def main():
    if not GROQ_API_KEY:
        log.error("GROQ_API_KEY not set in .env")
        sys.exit(1)

    client = AsyncOpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
    # Groq allows ~30 RPM; semaphore=5 gives ~300 RPM headroom with retries
    sem = asyncio.Semaphore(5)

    all_tasks = []
    counter = 0

    for job in JOBS:
        src = Path(job["source"])
        out = Path(job["output"])
        out.mkdir(parents=True, exist_ok=True)

        txt_files = sorted(src.glob("*.txt"))
        missing = [f for f in txt_files if not (out / f.name).exists()]
        log.info("%s → %d missing files", src.name, len(missing))

        for f in missing:
            counter += 1
            all_tasks.append((f, out, counter))

    total = len(all_tasks)
    log.info("Total files to translate: %d", total)
    log.info("Model: %s", GROQ_MODEL)
    log.info("---")

    tasks = [
        process_file(client, f, out, sem, idx, total)
        for f, out, idx in all_tasks
    ]
    await asyncio.gather(*tasks)

    log.info("=== Done! ===")
    log.info("P&R  → output/translated-hindi-p_r/")
    log.info("Contacts → output/translated-hindi-contacts/")


if __name__ == "__main__":
    asyncio.run(main())
