"""Rename paired notes/screenshots in jobs/9a1b22709820 - 1/ using the first words of each note.

Pairing key is the leading number in each filename:
  notes/<num>_en_US_...txt   <->   screenshots/<num> <text>.jpg

Output goes to notes_app/output/final_contact/{notes,screenshots}/ with a manifest.csv.
Originals are left untouched.
"""

from __future__ import annotations

import csv
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "output" / "jobs" / "9a1b22709820 - 1"
SRC_TXT = SRC_ROOT / "notes"
SRC_IMG = SRC_ROOT / "screenshots"

DST_ROOT = ROOT / "output" / "final_contact"
DST_TXT = DST_ROOT / "notes"
DST_IMG = DST_ROOT / "screenshots"
MANIFEST = DST_ROOT / "manifest.csv"

MAX_WORDS = 20
MIN_WORDS = 2

WORD_RE = re.compile(r"[a-z0-9]+")
LEADING_NUM_RE = re.compile(r"^(\d+)")


def tokenize(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def safe_name(words: list[str]) -> str:
    return " ".join(words)


def index_screenshots() -> dict[str, Path]:
    out: dict[str, Path] = {}
    for p in SRC_IMG.glob("*.jpg"):
        m = LEADING_NUM_RE.match(p.name)
        if m:
            out[m.group(1)] = p
    return out


def load_pairs() -> list[dict]:
    items = []
    img_index = index_screenshots()
    for txt_path in sorted(SRC_TXT.glob("*.txt")):
        m = LEADING_NUM_RE.match(txt_path.name)
        if not m:
            continue
        key = m.group(1)
        jpg_path = img_index.get(key)
        entry = {
            "original_id": key,
            "original_txt_name": txt_path.name,
            "original_jpg_name": jpg_path.name if jpg_path else "",
            "txt_path": txt_path,
            "jpg_path": jpg_path,
            "words": [],
            "status": "renamed",
            "new_name": "",
            "words_used": 0,
        }
        if jpg_path is None:
            entry["status"] = "skipped_missing_pair"
            items.append(entry)
            continue
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

    seen_full: dict[tuple[str, ...], dict] = {}
    for it in kept:
        key = tuple(it["words"])
        if key in seen_full:
            it["status"] = "dropped_duplicate"
        else:
            seen_full[key] = it

    survivors = [it for it in kept if it["status"] == "renamed"]
    assigned: dict[str, int] = {}
    remaining = list(survivors)
    k = MIN_WORDS
    while remaining and k <= MAX_WORDS:
        def prefix_at(it: dict, length: int) -> tuple[str, ...]:
            return tuple(it["words"][: min(length, len(it["words"]))])

        counts: dict[tuple[str, ...], int] = {}
        for it in survivors:
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

    if remaining:
        groups: dict[tuple[str, ...], list[dict]] = {}
        for it in remaining:
            length = min(MAX_WORDS, len(it["words"]))
            key = tuple(it["words"][:length])
            groups.setdefault(key, []).append(it)
        for key, group in groups.items():
            group.sort(key=lambda x: x["original_id"])
            winner = group[0]
            assigned[winner["original_id"]] = len(key)
            for loser in group[1:]:
                loser["status"] = "dropped_duplicate"

    for it in survivors:
        if it["status"] != "renamed":
            continue
        n = assigned.get(it["original_id"])
        if n is None:
            it["status"] = "dropped_duplicate"
            continue
        it["words_used"] = n
        it["new_name"] = safe_name(it["words"][:n])

    for it in items:
        if it["status"] == "dropped_duplicate":
            key = tuple(it["words"])
            survivor = seen_full.get(key)
            if survivor and survivor["status"] == "renamed":
                it["new_name"] = survivor["new_name"]
            else:
                it["new_name"] = ""


def copy_pairs(items: list[dict]) -> None:
    DST_TXT.mkdir(parents=True, exist_ok=True)
    DST_IMG.mkdir(parents=True, exist_ok=True)
    for it in items:
        if it["status"] != "renamed":
            continue
        new_base = it["new_name"]
        shutil.copy2(it["txt_path"], DST_TXT / f"{new_base}.txt")
        shutil.copy2(it["jpg_path"], DST_IMG / f"{new_base}.jpg")


def write_manifest(items: list[dict]) -> None:
    DST_ROOT.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "original_id",
            "original_txt_name",
            "original_jpg_name",
            "new_name",
            "words_used",
            "status",
        ])
        for it in sorted(items, key=lambda x: x["original_id"]):
            writer.writerow([
                it["original_id"],
                it["original_txt_name"],
                it["original_jpg_name"],
                it["new_name"],
                it["words_used"],
                it["status"],
            ])


def main() -> None:
    if not SRC_TXT.is_dir() or not SRC_IMG.is_dir():
        raise SystemExit(f"source folders not found under {SRC_ROOT}")

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
