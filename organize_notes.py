"""Rename paired txt/jpg files in Batch - 3 - Final - Contact notes.

Matches text files in `notes` with image files in `screenshots` within the same
subdirectory based on their numeric prefix.
Computes a unique word-prefix base name per note.
Copies both halves into a single output folder.
"""

import csv
import re
import shutil
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC_ROOT = ROOT / "output" / "Batch - 3 Final - P & R Notes"
DST_ROOT = SRC_ROOT / "organized"
DST_TXT = DST_ROOT / "text"
DST_IMG = DST_ROOT / "image"
MANIFEST = DST_ROOT / "manifest.csv"

MAX_WORDS = 6
MIN_WORDS = 2

WORD_RE = re.compile(r"[a-z0-9]+")

def tokenize(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())

def safe_name(words: list[str]) -> str:
    return " ".join(words)

def load_pairs() -> list[dict]:
    items = []
    
    # Iterate through all subdirectories
    for subdir in SRC_ROOT.iterdir():
        if not subdir.is_dir() or subdir.name == "organized":
            continue
            
        notes_dir = subdir / "notes"
        screenshots_dir = subdir / "screenshots"
        
        if not notes_dir.exists() or not screenshots_dir.exists():
            continue
            
        # Get mapping of prefix ID to image file
        image_map = {}
        for img_path in screenshots_dir.iterdir():
            if img_path.is_file():
                match = re.match(r"^(\d+)", img_path.name)
                if match:
                    image_map[match.group(1)] = img_path
                    
        # Find matching txt files
        for txt_path in notes_dir.glob("*.txt"):
            txt_match = re.match(r"^(\d+)", txt_path.name)
            if not txt_match:
                continue
                
            original_id = txt_match.group(1)
            
            entry = {
                "original_id": f"{subdir.name}_{original_id}", # ensure unique ID across subdirs
                "txt_path": txt_path,
                "jpg_path": None,
                "words": [],
                "status": "renamed",
                "new_name": "",
                "words_used": 0,
            }
            
            if original_id not in image_map:
                entry["status"] = "skipped_missing_pair"
                items.append(entry)
                continue
                
            entry["jpg_path"] = image_map[original_id]
            
            try:
                text = txt_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                entry["status"] = "skipped_missing_pair"
                items.append(entry)
                continue
                
            words = tokenize(text)
            if not words:
                entry["status"] = "skipped_empty_text"
                items.append(entry)
                continue
                
            entry["words"] = words
            items.append(entry)
            
    return items

def assign_unique_prefixes(items: list[dict]) -> None:
    kept = [it for it in items if it["status"] == "renamed"]

    # We will not drop any duplicates.
    assigned: dict[str, int] = {}
    remaining = list(kept)
    k = MIN_WORDS
    
    # We will use up to MAX_WORDS (e.g. 20 to allow "more than 5 to 6")
    MAX_WORDS_ALLOWED = 20
    
    while remaining and k <= MAX_WORDS_ALLOWED:
        def prefix_at(it: dict, length: int) -> tuple[str, ...]:
            return tuple(it["words"][: min(length, len(it["words"]))])

        counts: dict[tuple[str, ...], int] = {}
        for it in kept:
            p = prefix_at(it, k)
            counts[p] = counts.get(p, 0) + 1

        next_remaining = []
        for it in remaining:
            p = prefix_at(it, k)
            if counts[p] == 1:
                assigned[it["original_id"]] = min(k, len(it["words"]))
            else:
                next_remaining.append(it)
        remaining = next_remaining
        k += 1

    # For any that are still remaining, they either have identical text up to MAX_WORDS_ALLOWED
    # or are exact full-text duplicates. We just assign them MAX_WORDS_ALLOWED and we will 
    # disambiguate them with a numeric suffix later.
    for it in remaining:
        assigned[it["original_id"]] = min(MAX_WORDS_ALLOWED, len(it["words"]))

    # Now generate names and disambiguate
    used_names = set()
    for it in kept:
        n = assigned[it["original_id"]]
        it["words_used"] = n
        base_name = safe_name(it["words"][:n])
        
        # Ensure it is absolutely unique
        final_name = base_name
        counter = 2
        while final_name in used_names:
            final_name = f"{base_name} {counter}"
            counter += 1
            
        used_names.add(final_name)
        it["new_name"] = final_name

def ensure_absolute_uniqueness(items: list[dict]):
    # Since user wants absolutely unique names, and `assign_unique_prefixes` might drop
    # items if they are fully identical text. If they are identical text, the user might
    # still want them, or maybe it's fine to drop them as duplicates.
    # The `rename_pairs.py` drops full duplicates. We'll leave it as is, but ensure no collision on new_name.
    pass

def copy_pairs(items: list[dict]) -> None:
    DST_TXT.mkdir(parents=True, exist_ok=True)
    DST_IMG.mkdir(parents=True, exist_ok=True)
    for it in items:
        if it["status"] != "renamed":
            continue
        new_base = it["new_name"]
        
        # Determine image extension from source
        img_ext = it["jpg_path"].suffix
        
        shutil.copy2(it["txt_path"], DST_TXT / f"{new_base}.txt")
        shutil.copy2(it["jpg_path"], DST_IMG / f"{new_base}{img_ext}")

def write_manifest(items: list[dict]) -> None:
    DST_ROOT.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["original_id", "new_name", "words_used", "status", "txt_path", "img_path"])
        for it in sorted(items, key=lambda x: x["original_id"]):
            writer.writerow([it["original_id"], it["new_name"], it["words_used"], it["status"], str(it["txt_path"]), str(it.get("jpg_path", ""))])

def main() -> None:
    # First, let's clean up previous run
    if DST_ROOT.exists():
        shutil.rmtree(DST_ROOT)
        
    items = load_pairs()
    assign_unique_prefixes(items)
    copy_pairs(items)
    write_manifest(items)

    counts: dict[str, int] = {}
    for it in items:
        counts[it["status"]] = counts.get(it["status"], 0) + 1
    total = len(items)
    print(f"processed {total} txt files")
    for status, n in sorted(counts.items()):
        print(f"  {status}: {n}")
    print(f"output: {DST_ROOT}")
    print(f"manifest: {MANIFEST}")

if __name__ == "__main__":
    main()
