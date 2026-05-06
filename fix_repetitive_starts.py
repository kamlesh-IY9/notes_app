#!/usr/bin/env python3
"""Post-process organized P&R notes to fix repetitive starting words.

For each first-word that appears > MAX_PER_WORD times across batch_1 + batch_2:
  - Keep the first MAX_PER_WORD files as-is (sorted by filename, deterministic)
  - For the excess: swap the starting word → rename .txt + .jpg → re-render screenshot
  - Update manifest.csv with the new slug

Run from the project root:
    python fix_repetitive_starts.py
"""

import asyncio
import csv
import os
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.screenshot import render_screenshot, close_browser

ORGANIZED = PROJECT_ROOT / "output" / "Batch - 3 Final - P & R Notes" / "organized"
DB_PATH = PROJECT_ROOT / "output" / "app.sqlite"
MANIFEST_PATH = ORGANIZED / "manifest.csv"
BATCHES = [ORGANIZED / "batch_1", ORGANIZED / "batch_2"]

MAX_PER_WORD = 8

# Replacement phrases cycled deterministically (index % len).
# For "low": replaces the full "low key" 2-word prefix.
REPLACEMENTS = {
    # ── Pass 1: original repetitive words ──
    "gotta":    ["meant to", "supposed to", "tryna", "bout to"],
    "need":     ["meant to", "supposed to", "bout to", "have to"],
    "just":     ["btw", "fyi", "honestly", "actually", "apparently"],
    "told":     ["texted", "reminded", "messaged", "asked"],
    "thinking": ["wondering", "debating", "considering"],
    "so":       ["btw", "fyi", "anyway", "basically"],
    "gonna":    ["planning to", "bout to", "meant to"],
    "been":     ["keep", "still", "honestly"],
    "low":      ["kinda", "honestly", "actually"],
    "almost":   ["nearly", "meant to", "bout to"],
    "ok":       ["well", "honestly", "btw", "anyway"],
    "ask":      ["remind", "tell", "let"],
    "finally":  ["btw", "also", "fyi", "actually"],
    "dont":     ["cant", "wont", "shouldnt"],
    "saw":      ["noticed", "heard", "spotted"],
    "got":      ["picked up", "found", "heard about"],
    "schedule": ["book", "plan", "set up"],
    "remind":   ["tell", "ask", "let"],
    "update":   ["btw", "fyi", "tell"],
    "wondering": ["debating", "considering", "thinking abt"],
    # ── Pass 2: words that clustered after pass 1 ──
    "meant":    ["planning to", "trying to", "fixing to", "hoping to"],
    "bout":     ["close to", "nearly", "gettin", "about to"],
    "btw":      ["also", "anyway", "sidebar", "heads up"],
    "supposed": ["trying to", "hoping to", "aiming to", "fixing to"],
    "honestly": ["tbh", "ngl", "real talk", "lowkey"],
}


# ── helpers ───────────────────────────────────────────────────────────────────

def make_slug(text: str) -> str:
    first_line = text.split('\n')[0].strip()
    slug = re.sub(r'[^\w\s-]', '', first_line).strip()
    return slug[:40].rstrip()


def replace_start(content: str, first_key: str, new_phrase: str) -> str:
    """Replace the starting word (or 'low key' 2-word unit) in content."""
    stripped = content.lstrip()
    leading = content[: len(content) - len(stripped)]

    if first_key == "low":
        prefix = "low key"
        if stripped.lower().startswith(prefix):
            rest = stripped[len(prefix):]
        else:
            rest = stripped[3:] if len(stripped) > 3 else ""
        return leading + new_phrase + (" " + rest.lstrip() if rest.strip() else "")

    parts = stripped.split(None, 1)
    if len(parts) == 1:
        return leading + new_phrase
    result = leading + new_phrase + " " + parts[1]
    # Collapse "to to" that arises when replacement ends with "to" and rest starts with "to"
    result = re.sub(r'\bto\s+to\b', 'to', result, count=1, flags=re.IGNORECASE)
    return result


def query_db(original_id: str):
    parts = original_id.rsplit("_", 1)
    job_id, global_id = parts[0], int(parts[1])
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute(
        "SELECT app_type, theme, has_title, note_date, connectivity "
        "FROM entries WHERE job_id=? AND global_id=?",
        (job_id, global_id),
    )
    row = c.fetchone()
    conn.close()
    return row


# ── scanning ──────────────────────────────────────────────────────────────────

def scan_files():
    """Return sorted list of (slug, batch_path, txt_path, img_path)."""
    files = []
    for batch in BATCHES:
        txt_dir = batch / "text"
        img_dir = batch / "image"
        for fn in sorted(os.listdir(txt_dir)):
            if not fn.endswith(".txt"):
                continue
            slug = fn[:-4]
            files.append((slug, batch, txt_dir / fn, img_dir / (slug + ".jpg")))
    return files


def identify_fixes(files):
    """Return list of (first_key, slug, batch, txt_path, img_path) for notes to fix."""
    word_groups: dict[str, list] = defaultdict(list)
    for slug, batch, txt_path, img_path in files:
        words = slug.split()
        if not words:
            continue
        key = words[0].lower()
        word_groups[key].append((slug, batch, txt_path, img_path))

    to_fix = []
    for key, items in word_groups.items():
        if len(items) > MAX_PER_WORD and key in REPLACEMENTS:
            excess = items[MAX_PER_WORD:]
            for item in excess:
                to_fix.append((key, *item))
    return to_fix


# ── per-note fix ──────────────────────────────────────────────────────────────

async def fix_one(
    first_key: str,
    slug: str,
    batch: Path,
    txt_path: Path,
    img_path: Path,
    fix_index: int,
    rows: list,
    slug_to_row_idx: dict,
    used_slugs: set,
) -> bool:
    try:
        content = txt_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        print(f"  SKIP (txt missing): {slug}")
        return False

    new_phrase = REPLACEMENTS[first_key][fix_index % len(REPLACEMENTS[first_key])]
    new_content = replace_start(content, first_key, new_phrase)
    new_slug_base = make_slug(new_content)

    # Resolve slug collision
    new_slug = new_slug_base
    collision_n = 1
    while new_slug in used_slugs and new_slug != slug:
        new_slug = f"{new_slug_base} {collision_n}"
        collision_n += 1

    # Remove old slug, register new
    used_slugs.discard(slug)
    used_slugs.add(new_slug)

    new_txt_path = batch / "text" / (new_slug + ".txt")
    new_img_path = batch / "image" / (new_slug + ".jpg")

    # Write new txt
    new_txt_path.write_text(new_content, encoding="utf-8")
    if txt_path != new_txt_path and txt_path.exists():
        txt_path.unlink()

    # Fetch DB metadata for screenshot re-render
    row_idx = slug_to_row_idx.get(slug)
    if row_idx is None:
        print(f"  SKIP (not in manifest): {slug}")
        return False

    original_id = rows[row_idx]["original_id"]
    db_row = query_db(original_id)

    if db_row is None:
        print(f"  WARNING: no DB entry for {original_id} — txt updated, screenshot skipped")
        rows[row_idx]["new_name"] = new_slug
        return True

    app_type, theme, has_title, note_date_str, connectivity = db_row
    has_title = bool(has_title)
    note_date = datetime.fromisoformat(note_date_str)

    # Re-render screenshot
    await render_screenshot(
        note_text=new_content,
        has_title=has_title,
        app_type=app_type,
        theme=theme,
        note_date=note_date,
        connectivity=connectivity,
        output_path=str(new_img_path),
    )

    # Remove old image
    if img_path.exists() and img_path != new_img_path:
        img_path.unlink()

    # Update manifest row
    rows[row_idx]["new_name"] = new_slug

    print(f"  {first_key}: '{slug}' → '{new_slug}'")
    return True


# ── main ──────────────────────────────────────────────────────────────────────

async def main():
    rows, fieldnames = [], []
    with open(MANIFEST_PATH, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # slug → manifest row index (for updates)
    slug_to_row_idx = {r["new_name"]: i for i, r in enumerate(rows)}

    files = scan_files()
    to_fix = identify_fixes(files)

    used_slugs: set = {slug for slug, *_ in files}

    print(f"Total notes: {len(files)}")
    print(f"Notes to fix: {len(to_fix)}\n")

    if not to_fix:
        print("Nothing to fix.")
        return

    word_fix_counts: dict[str, int] = defaultdict(int)
    summary: dict[str, int] = defaultdict(int)
    errors = 0

    for first_key, slug, batch, txt_path, img_path in to_fix:
        fix_index = word_fix_counts[first_key]
        word_fix_counts[first_key] += 1

        ok = await fix_one(
            first_key, slug, batch, txt_path, img_path,
            fix_index, rows, slug_to_row_idx, used_slugs,
        )
        if ok:
            summary[first_key] += 1
        else:
            errors += 1

    # Save manifest
    with open(MANIFEST_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("\n── Summary ──────────────────")
    for word, count in sorted(summary.items(), key=lambda x: -x[1]):
        print(f"  {word:12s}: {count} fixed")
    print(f"  errors     : {errors}")
    print(f"\nmanifest updated: {MANIFEST_PATH}")

    await close_browser()


if __name__ == "__main__":
    asyncio.run(main())
