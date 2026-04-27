import os, re, shutil, unicodedata

DIRS = [
    "/home/kamleshpatil/Desktop/Test - M/notes_app/output/jobs/9d46ad272be2 - 1",
    "/home/kamleshpatil/Desktop/Test - M/notes_app/output/jobs/9235a390b240 - 2",
    "/home/kamleshpatil/Desktop/Test - M/notes_app/output/jobs/15ba67a0d7b6 - 3",
    "/home/kamleshpatil/Desktop/Test - M/notes_app/output/jobs/2c109bbc5564 - 4",
]

FINAL_DIR = "/home/kamleshpatil/Desktop/Test - M/notes_app/output/final"
FINAL_TXT = os.path.join(FINAL_DIR, "txt")
FINAL_IMG = os.path.join(FINAL_DIR, "images")

REL_KEYWORDS = [
    "mom", "dad", "sister", "brother", "friend", "boss", "uncle", "aunt",
    "cousin", "wife", "husband", "girlfriend", "boyfriend", "roommate",
    "coworker", "colleague", "partner", "kid", "son", "daughter", "grandma",
    "grandpa", "niece", "nephew", "fiance", "fiancee", "mentor", "neighbor",
    "papa", "mama", "sis", "bro",
    # Slang/informal that ARE valid relationships:
    "bestie", "babe", "cuz", "pops", "father", "granny", "nana", "auntie",
    "housemate", "buddy", "manager", "fiancé", "fiancée", "daugter",
    "mother", "sisterout",
]

NOSTALGIA = ["5 year", "long time", "after so long", "nostalgia",
             "havent seen", "haven't seen", "years since", "reconnect"]

def has_non_english(text):
    for ch in text:
        if ord(ch) < 128:
            continue
        cat = unicodedata.category(ch)
        if cat.startswith("L"):
            name = unicodedata.name(ch, "")
            if any(s in name for s in ["CJK", "HANGUL", "ARABIC", "DEVANAGARI",
                                        "HIRAGANA", "KATAKANA", "THAI", "CYRILLIC"]):
                return True
    return False

def is_clean(text):
    lines = [l for l in text.split("\n") if l.strip()]
    text_lower = text.lower()

    # Too many lines
    if len(lines) > 5:
        return False

    # Line too wordy
    for l in lines:
        if len(l.split()) > 18:
            return False

    # Nostalgia
    for phrase in NOSTALGIA:
        if phrase in text_lower:
            return False

    # Missing relationship
    has_rel = any(re.search(r'(?:^|[^a-z])' + k, text_lower) for k in REL_KEYWORDS)
    if not has_rel:
        return False

    # Non-English
    if has_non_english(text):
        return False

    # Too formal
    alpha = [c for c in text if c.isalpha()]
    if alpha:
        upper_r = sum(1 for c in alpha if c.isupper()) / len(alpha)
        if upper_r > 0.25:
            return False

    return True

# Create output dirs
os.makedirs(FINAL_TXT, exist_ok=True)
os.makedirs(FINAL_IMG, exist_ok=True)

total = 0
copied = 0
skipped = 0
no_img = 0

for d in DIRS:
    notes_dir = os.path.join(d, "notes")
    screenshots_dir = os.path.join(d, "screenshots")
    job_label = os.path.basename(d)

    if not os.path.isdir(notes_dir):
        print(f"[SKIP] {job_label}: no notes/ dir")
        continue

    # Build a map of note_id -> screenshot filename
    img_map = {}
    if os.path.isdir(screenshots_dir):
        for img_fname in os.listdir(screenshots_dir):
            match = re.match(r'^(\d+)', img_fname)
            if match:
                img_map[match.group(1)] = img_fname

    for txt_fname in sorted(os.listdir(notes_dir)):
        if not txt_fname.endswith(".txt"):
            continue

        total += 1
        # Extract note ID (the leading number)
        match = re.match(r'^(\d+)', txt_fname)
        if not match:
            skipped += 1
            continue
        note_id = match.group(1)

        # Read text and check QA
        txt_path = os.path.join(notes_dir, txt_fname)
        text = open(txt_path).read().strip()

        if not is_clean(text):
            skipped += 1
            continue

        # Find matching image
        if note_id not in img_map:
            no_img += 1
            continue

        img_fname = img_map[note_id]
        img_path = os.path.join(screenshots_dir, img_fname)

        # Use job-prefix to avoid ID collisions across jobs
        job_short = job_label.split(" - ")[1] if " - " in job_label else "0"
        final_id = f"job{job_short}_{note_id}"

        # Copy text file
        shutil.copy2(txt_path, os.path.join(FINAL_TXT, f"{final_id}.txt"))

        # Copy image file (keep original extension)
        ext = os.path.splitext(img_fname)[1]
        shutil.copy2(img_path, os.path.join(FINAL_IMG, f"{final_id}{ext}"))

        copied += 1

print(f"\n{'='*60}")
print(f"DONE!")
print(f"{'='*60}")
print(f"Total scanned: {total}")
print(f"Copied (clean): {copied}")
print(f"Skipped (QA fail): {skipped}")
print(f"Missing image: {no_img}")
print(f"\nOutput:")
print(f"  Text files:  {FINAL_TXT}")
print(f"  Images:      {FINAL_IMG}")
print(f"\nVerification:")
txt_count = len([f for f in os.listdir(FINAL_TXT) if f.endswith('.txt')])
img_count = len([f for f in os.listdir(FINAL_IMG)])
print(f"  txt/ count:    {txt_count}")
print(f"  images/ count: {img_count}")
print(f"  Match: {'YES ✅' if txt_count == img_count else 'NO ❌'}")
