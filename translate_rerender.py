"""
translate_rerender.py — Translate English note .txt files to Hindi Devanagari
using Ollama (local, zero API keys), then re-render .jpg screenshots.

Run from the project root:
  python3 translate_rerender.py <source_notes_dir> <output_dir>

Examples:
  python3 translate_rerender.py \
    "output/sample - hindi - p_r notes/d296c257f0d0 - hindi - p-r/notes" \
    "output/translated-hindi-p_r"

  python3 translate_rerender.py \
    "output/sample hindi - contacts notes/a8cd6a175de0 - contact - notes/notes" \
    "output/translated-hindi-contacts"
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

from openai import AsyncOpenAI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "gemma3:latest")
DB_PATH         = os.getenv("DB_PATH", "output/app.sqlite")

TRANSLATION_SYSTEM = """You are a Hindi translator. Translate the English phone note to natural, casual, informal Hindi Devanagari.

RULES:
- Output ONLY Hindi Devanagari script
- Keep every line break exactly as-is — do NOT merge lines
- Keep proper names (people, places, brands) in English/Roman
- Keep numbers, phone numbers, dates as-is
- Keep English abbreviations like ok, lol, idk, rn, tbh — Indians use them
- Do NOT add formality — casual everyday Hindi
- Output ONLY the translated text, nothing else"""


def _has_devanagari(text: str) -> bool:
    return bool(re.search(r"[ऀ-ॿ]", text))


async def translate(client: AsyncOpenAI, text: str) -> str:
    """Translate one note via Ollama. Returns original on total failure."""
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
                    model=OLLAMA_MODEL,
                    messages=[
                        {"role": "system", "content": TRANSLATION_SYSTEM},
                        {"role": "user",   "content": prompt},
                    ],
                    temperature=0.2,
                    max_tokens=500,
                ),
                timeout=300.0,
            )
            result = resp.choices[0].message.content.strip().strip('"').strip("'")
            if result.startswith("```"):
                parts = result.split("```")
                result = parts[1].strip() if len(parts) > 1 else parts[0][3:].strip()
            if _has_devanagari(result):
                return result
            log.warning("Attempt %d — no Devanagari in output, retrying", attempt + 1)
        except asyncio.TimeoutError:
            log.warning("Attempt %d — Ollama timed out", attempt + 1)
        except Exception as e:
            log.warning("Attempt %d — %s", attempt + 1, e)
    log.error("All attempts failed — keeping English text")
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
        weights=[70, 15, 10, 5], k=1
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
            log.warning("Empty file — skipping %s", txt_path.name)
            return

        hindi = await translate(client, english)

        # Save translated txt (same filename)
        out_txt = out_dir / txt_path.name
        out_txt.write_text(hindi, encoding="utf-8")

        # Get screenshot metadata
        m = re.match(r"^(\d+)_.*?_(\d+)\.txt$", txt_path.name)
        global_id  = int(m.group(1)) if m else 0
        entry_num  = int(m.group(2)) if m else 0
        meta = _db_metadata(global_id, entry_num) or _random_metadata()

        app_type    = meta["app_type"]
        theme       = meta["theme"]
        has_title   = bool(meta["has_title"])
        connectivity= meta.get("connectivity", "wifi_cellular")
        try:
            note_date = datetime.fromisoformat(meta["note_date"])
        except Exception:
            note_date = datetime.now()

        jpg_name = txt_path.stem + ".jpg"
        out_jpg  = out_dir / jpg_name

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

        log.info("  → saved %s + %s", out_txt.name, jpg_name)


async def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    source_dir = Path(sys.argv[1])
    out_dir    = Path(sys.argv[2])

    if not source_dir.exists():
        log.error("Source directory not found: %s", source_dir)
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)

    txt_files = sorted(source_dir.glob("*.txt"))
    if not txt_files:
        log.error("No .txt files found in %s", source_dir)
        sys.exit(1)

    total = len(txt_files)
    log.info("Files to process : %d", total)
    log.info("Ollama model     : %s  (%s)", OLLAMA_MODEL, OLLAMA_BASE_URL)
    log.info("Output directory : %s", out_dir)
    log.info("---")

    client = AsyncOpenAI(api_key="ollama", base_url=OLLAMA_BASE_URL)
    # semaphore=1 — CPU Ollama can only do one inference at a time
    sem = asyncio.Semaphore(1)

    tasks = [
        process_file(client, f, out_dir, sem, i + 1, total)
        for i, f in enumerate(txt_files)
    ]
    await asyncio.gather(*tasks)

    log.info("=== All done! ===  Output: %s", out_dir)


if __name__ == "__main__":
    asyncio.run(main())
