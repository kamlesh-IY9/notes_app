"""
retranslate_missing.py — Fix all output files that are still in English.
Uses Google Translate via deep_translator (free, no API key needed).
Then re-renders screenshots with Devanagari font.
"""

import asyncio
import logging
import os
import re
import sqlite3
import random
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from deep_translator import GoogleTranslator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DB_PATH = "output/app.sqlite"

OUTPUTS = [
    "output/translated-hindi-p_r",
    "output/translated-hindi-contacts",
]

SOURCES = {
    "output/translated-hindi-p_r": "output/sample - hindi - p_r notes/d296c257f0d0 - hindi - p-r/notes",
    "output/translated-hindi-contacts": "output/sample hindi - contacts notes/a8cd6a175de0 - contact - notes/notes",
}


def _has_devanagari(text: str) -> bool:
    return len(re.findall(r"[ऀ-ॿ]", text)) >= 5


def translate_with_google(text: str) -> str:
    """Translate line-by-line to preserve structure. Free, no key needed.
    Everything goes to Devanagari — including names."""
    lines = text.split("\n")
    translated_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            translated_lines.append(line)
            continue
        # Skip lines that are purely numbers/symbols/email/phone
        if re.match(r"^[\d\s\+\-\(\)\.\@\/\:\#]+$", stripped):
            translated_lines.append(line)
            continue
        try:
            result = GoogleTranslator(source="en", target="hi").translate(stripped)
            if result and re.search(r"[ऀ-ॿ]", result):
                translated_lines.append(result)
            else:
                translated_lines.append(line)
            time.sleep(0.1)  # be polite to free API
        except Exception as e:
            log.warning("Google translate failed for line '%s': %s", stripped[:40], e)
            translated_lines.append(line)
    return "\n".join(translated_lines)


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


async def render_jpg(txt_path: Path, hindi: str, out_dir: Path):
    m = re.match(r"^(\d+)_.*?_(\d+)\.txt$", txt_path.name)
    global_id = int(m.group(1)) if m else 0
    entry_num = int(m.group(2)) if m else 0
    meta = _db_metadata(global_id, entry_num) or _random_metadata()

    try:
        note_date = datetime.fromisoformat(meta["note_date"])
    except Exception:
        note_date = datetime.now()

    out_jpg = out_dir / (txt_path.stem + ".jpg")

    from backend.core.screenshot import render_screenshot
    try:
        await render_screenshot(
            note_text=hindi,
            has_title=bool(meta["has_title"]),
            app_type=meta["app_type"],
            theme=meta["theme"],
            note_date=note_date,
            connectivity=meta.get("connectivity", "wifi_cellular"),
            output_path=str(out_jpg),
            language="hindi",
        )
    except Exception as e:
        log.error("Screenshot failed for %s: %s", txt_path.name, e)


async def main():
    tasks_to_do = []

    for out_dir_str in OUTPUTS:
        out_dir = Path(out_dir_str)
        src_dir = Path(SOURCES[out_dir_str])

        for out_txt in sorted(out_dir.glob("*.txt")):
            # Always use original English source for fresh translation
            src_file = src_dir / out_txt.name
            if src_file.exists():
                original = src_file.read_text(encoding="utf-8").strip()
            else:
                original = out_txt.read_text(encoding="utf-8").strip()

            tasks_to_do.append((out_txt, original, out_dir))

    total = len(tasks_to_do)
    log.info("Files to retranslate (all, names → Devanagari): %d", total)
    log.info("Using Google Translate (free, no key needed)")
    log.info("---")

    for idx, (out_txt, original, out_dir) in enumerate(tasks_to_do, 1):
        log.info("[%d/%d] %s", idx, total, out_txt.name)
        hindi = translate_with_google(original)
        out_txt.write_text(hindi, encoding="utf-8")
        await render_jpg(out_txt, hindi, out_dir)
        log.info("  → done")

    log.info("=== All retranslated! ===")


if __name__ == "__main__":
    asyncio.run(main())
