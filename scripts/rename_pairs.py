"""Rename paired txt/jpg files in notes_app/output/final/ using the first words of each note.

Reads notes_app/output/final/{txt,images}/, computes a unique word-prefix base name
per note, and copies both halves of each pair into notes_app/output/final_named/.
Originals are left untouched. A manifest.csv is written next to the new folders.
"""

from __future__ import annotations

import csv
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_TXT = ROOT / "output" / "final" / "txt"
SRC_IMG = ROOT / "output" / "final" / "images"
DST_ROOT = ROOT / "output" / "final_named"
DST_TXT = DST_ROOT / "txt"
DST_IMG = DST_ROOT / "images"
MANIFEST = DST_ROOT / "manifest.csv"

MAX_WORDS = 20
MIN_WORDS = 2

WORD_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def safe_name(words: list[str]) -> str:
    # Filenames on Linux only forbid '/' and NUL. Tokenizer already keeps it to
    # [a-z0-9]+, so spaces between words are the only joiner needed.
    return " ".join(words)


def load_pairs() -> list[dict]:
    items = []
    for txt_path in sorted(SRC_TXT.glob("*.txt")):
        original_id = txt_path.stem
        jpg_path = SRC_IMG / f"{original_id}.jpg"
        entry = {
            "original_id": original_id,
            "txt_path": txt_path,
            "jpg_path": jpg_path,
            "words": [],
            "status": "renamed",
            "new_name": "",
            "words_used": 0,
        }
        if not jpg_path.exists():
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
    """For each kept item, pick the shortest word-prefix unique among all kept items.

    Handles the "one note is a prefix of another" case by giving the shorter note
    its full text and forcing the longer note to extend at least one word past it.
    True content duplicates (full text matches another note's full text or full
    prefix at the cap) are marked dropped_duplicate; first occurrence wins.
    """
    kept = [it for it in items if it["status"] == "renamed"]

    # Group by full-text equality first to settle exact duplicates deterministically.
    seen_full: dict[tuple[str, ...], dict] = {}
    for it in kept:
        key = tuple(it["words"])
        if key in seen_full:
            it["status"] = "dropped_duplicate"
            it["new_name"] = seen_full[key]["original_id"]  # placeholder, overwritten below
        else:
            seen_full[key] = it

    survivors = [it for it in kept if it["status"] == "renamed"]

    # Now find the smallest K for each survivor such that no other survivor shares the same K-prefix.
    # If a survivor's words run out before becoming unique (because another survivor's longer prefix
    # equals its full text), the shorter one keeps its full text and the longer one must use K+1.
    # Implementation: iterate K from 2 upward; assign K to any survivor whose K-prefix is unique
    # among survivors that haven't been assigned yet AND whose prefix at length min(K, len(other)) doesn't collide.

    assigned: dict[str, int] = {}  # original_id -> K
    remaining = list(survivors)
    k = MIN_WORDS
    while remaining and k <= MAX_WORDS:
        # Build prefix counts at length k across ALL survivors (using min(k, len(words)) so shorter
        # notes contribute their full text as their prefix at this stage).
        def prefix_at(it: dict, length: int) -> tuple[str, ...]:
            return tuple(it["words"][: min(length, len(it["words"]))])

        counts: dict[tuple[str, ...], int] = {}
        for it in survivors:
            p = prefix_at(it, k)
            counts[p] = counts.get(p, 0) + 1

        next_remaining = []
        for it in remaining:
            p = prefix_at(it, k)
            # Unique at this k AND the note has at least k words OR it is shorter than k
            # AND no other survivor shares this exact prefix (including longer notes whose first k
            # words equal this short note's full text — counts[p] > 1 catches that).
            if counts[p] == 1:
                # If this note is shorter than k (len(words) < k) and there exists a longer note
                # whose first len(words) words equal this note's words, counts[p] would already be > 1.
                # So uniqueness here is real.
                assigned[it["original_id"]] = min(k, len(it["words"]))
            else:
                next_remaining.append(it)
        remaining = next_remaining
        k += 1

    # Anything still remaining at MAX_WORDS is a near-duplicate; keep the first by original_id order
    # and drop the rest.
    if remaining:
        # Group remaining by their prefix at MAX_WORDS (or full length if shorter)
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

    # Materialize new_name and words_used on each survivor.
    for it in survivors:
        if it["status"] != "renamed":
            continue
        n = assigned.get(it["original_id"])
        if n is None:
            it["status"] = "dropped_duplicate"
            continue
        it["words_used"] = n
        it["new_name"] = safe_name(it["words"][:n])

    # Clear the placeholder new_name on dropped duplicates.
    for it in items:
        if it["status"] == "dropped_duplicate":
            # Leave new_name pointing at the survivor for traceability.
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
        writer.writerow(["original_id", "new_name", "words_used", "status"])
        for it in sorted(items, key=lambda x: x["original_id"]):
            writer.writerow([it["original_id"], it["new_name"], it["words_used"], it["status"]])


def main() -> None:
    if not SRC_TXT.is_dir() or not SRC_IMG.is_dir():
        raise SystemExit(f"source folders not found under {SRC_TXT.parent}")

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
