"""
translate_to_hindi.py — Translate English .txt notes to Hindi Devanagari
and re-render .jpg screenshots. Uses Google Translate (free, no API key).

Every word — including names — is converted to Devanagari.
Only pure numbers, phone numbers, and email addresses stay as-is.

Usage:
  python3 translate_to_hindi.py <source_notes_dir> <output_dir>

Examples:
  python3 translate_to_hindi.py \\
    "output/sample - hindi - p_r notes/d296c257f0d0 - hindi - p-r/notes" \\
    "output/my-hindi-p_r"

  python3 translate_to_hindi.py \\
    "output/sample hindi - contacts notes/a8cd6a175de0 - contact - notes/notes" \\
    "output/my-hindi-contacts"
"""

import asyncio
import logging
import os
import re
import sqlite3
import random
import sys
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

DB_PATH = os.getenv("DB_PATH", "output/app.sqlite")


def translate_to_hindi(text: str) -> str:
    """Translate all text to Hindi Devanagari line-by-line.
    Only pure number/email lines are kept as-is."""
    lines = text.split("\n")
    translated = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            translated.append(line)
            continue
        # Keep lines that are purely numbers, phone, email, symbols
        if re.match(r"^[\d\s\+\-\(\)\.\@\/\:\#\_]+$", stripped):
            translated.append(line)
            continue
        try:
            result = GoogleTranslator(source="en", target="hi").translate(stripped)
            if result and re.search(r"[ऀ-ॿ]", result):
                translated.append(result)
            else:
                translated.append(line)
            time.sleep(0.1)
        except Exception as e:
            log.warning("Translation failed for '%s': %s", stripped[:40], e)
            translated.append(line)
    return "\n".join(translated)


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


async def render_jpg(txt_name: str, hindi: str, out_dir: Path):
    m = re.match(r"^(\d+)_.*?_(\d+)\.txt$", txt_name)
    global_id = int(m.group(1)) if m else 0
    entry_num = int(m.group(2)) if m else 0
    meta = _db_metadata(global_id, entry_num) or _random_metadata()

    try:
        note_date = datetime.fromisoformat(meta["note_date"])
    except Exception:
        note_date = datetime.now()

    out_jpg = out_dir / (Path(txt_name).stem + ".jpg")

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
        log.error("Screenshot failed for %s: %s", txt_name, e)


async def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    source_dir = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])

    if not source_dir.exists():
        log.error("Source directory not found: %s", source_dir)
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)

    txt_files = sorted(source_dir.glob("*.txt"))
    if not txt_files:
        log.error("No .txt files found in %s", source_dir)
        sys.exit(1)

    total = len(txt_files)
    log.info("Files to translate : %d", total)
    log.info("Output directory   : %s", out_dir)
    log.info("Translator         : Google Translate (free, no key needed)")
    log.info("---")

    for idx, txt_path in enumerate(txt_files, 1):
        log.info("[%d/%d] %s", idx, total, txt_path.name)

        english = txt_path.read_text(encoding="utf-8").strip()
        if not english:
            log.warning("Empty file — skipping")
            continue

        hindi = translate_to_hindi(english)

        out_txt = out_dir / txt_path.name
        out_txt.write_text(hindi, encoding="utf-8")

        await render_jpg(txt_path.name, hindi, out_dir)
        log.info("  → saved %s + %s", out_txt.name, out_txt.stem + ".jpg")

    log.info("=== Done! Output: %s ===", out_dir)


if __name__ == "__main__":
    asyncio.run(main())
