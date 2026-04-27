import os, re, unicodedata

DIRS = [
    "/home/kamleshpatil/Desktop/Test - M/notes_app/output/jobs/9d46ad272be2 - 1",
    "/home/kamleshpatil/Desktop/Test - M/notes_app/output/jobs/9235a390b240 - 2",
    "/home/kamleshpatil/Desktop/Test - M/notes_app/output/jobs/15ba67a0d7b6 - 3",
    "/home/kamleshpatil/Desktop/Test - M/notes_app/output/jobs/2c109bbc5564 - 4",
]

REL_KEYWORDS = [
    "mom", "dad", "sister", "brother", "friend", "boss", "uncle", "aunt",
    "cousin", "wife", "husband", "girlfriend", "boyfriend", "roommate",
    "coworker", "colleague", "partner", "kid", "son", "daughter", "grandma",
    "grandpa", "niece", "nephew", "fiance", "fiancee", "mentor", "neighbor",
    "papa", "mama", "sis", "bro",
]

NOSTALGIA = ["5 year", "long time", "after so long", "nostalgia",
             "havent seen", "haven't seen", "years since", "reconnect",
             "catch up after", "met up after"]

def has_non_english(text):
    """Detect Chinese, Japanese, Korean, Arabic, Hindi, or other non-Latin scripts."""
    non_latin = []
    for ch in text:
        if ord(ch) < 128:
            continue
        cat = unicodedata.category(ch)
        if cat.startswith("L"):  # Letter category
            try:
                name = unicodedata.name(ch, "")
            except:
                name = ""
            if any(s in name for s in ["CJK", "HANGUL", "ARABIC", "DEVANAGARI",
                                        "HIRAGANA", "KATAKANA", "THAI", "CYRILLIC"]):
                non_latin.append(ch)
    return non_latin

total = 0
flagged = []

for d in DIRS:
    notes_dir = os.path.join(d, "notes")
    job_label = os.path.basename(d)
    if not os.path.isdir(notes_dir):
        print(f"[SKIP] {job_label}: no notes/ dir")
        continue
    for fname in sorted(os.listdir(notes_dir)):
        if not fname.endswith(".txt"):
            continue
        fpath = os.path.join(notes_dir, fname)
        text = open(fpath).read().strip()
        total += 1
        lines = [l for l in text.split("\n") if l.strip()]
        text_lower = text.lower()
        note_id = fname.replace(".txt", "")
        issues = []

        # 1) Too many lines
        if len(lines) > 5:
            issues.append(f"TOO_LONG ({len(lines)} lines)")

        # 2) Any line too wordy (not a fragment)
        for i, l in enumerate(lines):
            wc = len(l.split())
            if wc > 16:
                issues.append(f"LINE_WORDY (line {i+1}: {wc} words)")
                break

        # 3) Nostalgia / reunion
        for phrase in NOSTALGIA:
            if phrase in text_lower:
                issues.append(f"NOSTALGIA ('{phrase}')")
                break

        # 4) Missing relationship label
        has_rel = any(re.search(r'\b' + k + r'\b', text_lower) for k in REL_KEYWORDS)
        if not has_rel:
            issues.append("NO_RELATIONSHIP")

        # 5) Non-English / Chinese / foreign script
        foreign = has_non_english(text)
        if foreign:
            sample = "".join(foreign[:10])
            issues.append(f"NON_ENGLISH ({sample})")

        # 6) Too formal (too much uppercase)
        alpha = [c for c in text if c.isalpha()]
        if alpha:
            upper_r = sum(1 for c in alpha if c.isupper()) / len(alpha)
            if upper_r > 0.25:
                issues.append(f"TOO_FORMAL ({upper_r:.0%} uppercase)")

        if issues:
            flagged.append((job_label, note_id, issues, text))

# ── Report ──
print("=" * 72)
print(f"QA REPORT: {total} notes scanned across {len(DIRS)} jobs")
print("=" * 72)

# Category summary
cats = {}
for _, nid, issues, _ in flagged:
    for iss in issues:
        tag = iss.split("(")[0].strip().split(" ")[0]
        cats.setdefault(tag, []).append(nid)

pass_count = total - len(flagged)
pct = (pass_count / total * 100) if total else 0
print(f"\nPASSED: {pass_count} / {total} ({pct:.1f}%)")
print(f"FLAGGED: {len(flagged)} / {total}\n")

print("── Issues by Category ──")
for cat, items in sorted(cats.items(), key=lambda x: -len(x[1])):
    print(f"  {cat}: {len(items)} notes")

print(f"\n── Flagged Notes (note IDs for your review) ──")
for job, nid, issues, text in flagged:
    short = text.replace("\n", " | ")[:100]
    print(f"\n  [{job}] {nid}")
    print(f"    Issues: {', '.join(issues)}")
    print(f"    Text: {short}")

print(f"\n{'=' * 72}")
print(f"SEND TO LLM: The {len(flagged)} flagged note IDs listed above.")
print(f"CLEAN NOTES: {pass_count} notes are ready to ship.")
print(f"{'=' * 72}")
