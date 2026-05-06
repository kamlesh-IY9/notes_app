"""Stylometric jitter — post-processing to introduce natural imperfections."""

import random
import re
import logging

log = logging.getLogger(__name__)

# Adjacent keys on QWERTY for realistic typos
ADJACENT_KEYS = {
    'a': 'sq', 'b': 'vn', 'c': 'xv', 'd': 'sf', 'e': 'wr', 'f': 'dg',
    'g': 'fh', 'h': 'gj', 'i': 'uo', 'j': 'hk', 'k': 'jl', 'l': 'k',
    'm': 'n', 'n': 'bm', 'o': 'ip', 'p': 'o', 'q': 'w', 'r': 'et',
    's': 'ad', 't': 'ry', 'u': 'yi', 'v': 'cb', 'w': 'qe', 'x': 'zc',
    'y': 'tu', 'z': 'x',
}


def apply_jitter(note: str, persona: dict, style: dict) -> str:
    """Apply stylometric jitter to make the note look more human-typed.
    
    Applies persona quirks deterministically, plus random micro-imperfections.
    """
    quirks = persona.get("voice_quirks", [])

    # 1. Kill em dashes (belt AND suspenders)
    note = re.sub(r'[—–]', ', ', note)
    note = re.sub(r'\s*,\s*,', ',', note)  # Clean double commas

    # 2. Apply persona quirks
    if "lowercase_starts" in quirks:
        lines = note.split('\n')
        new_lines = []
        for i, line in enumerate(lines):
            # Don't lowercase the title (first line)
            if i > 0 and line and random.random() < 0.6:
                new_lines.append(line[0].lower() + line[1:] if len(line) > 1 else line.lower())
            else:
                new_lines.append(line)
        note = '\n'.join(new_lines)

    if "drop_apostrophes" in quirks:
        replacements = {
            "don't": "dont", "can't": "cant", "won't": "wont",
            "I'm": "Im", "I'll": "Ill", "he's": "hes", "she's": "shes",
            "it's": "its", "that's": "thats", "what's": "whats",
            "didn't": "didnt", "wasn't": "wasnt", "isn't": "isnt",
            "they're": "theyre", "we're": "were", "you're": "youre",
            "there's": "theres", "here's": "heres",
            "Don't": "Dont", "Can't": "Cant", "Won't": "Wont",
        }
        for old, new in replacements.items():
            if random.random() < 0.5:  # Don't replace ALL of them
                note = note.replace(old, new)

    if "use_ampersand" in quirks:
        # Replace ~50% of "and" with "&"
        lines = note.split('\n')
        new_lines = []
        for line in lines:
            words = line.split(' ')
            new_words = []
            for w in words:
                if w.lower() == "and" and random.random() < 0.4:
                    new_words.append("&")
                else:
                    new_words.append(w)
            new_lines.append(' '.join(new_words))
        note = '\n'.join(new_lines)

    if "no_end_periods" in quirks:
        lines = note.split('\n')
        new_lines = []
        for line in lines:
            if line.endswith('.') and random.random() < 0.7:
                new_lines.append(line[:-1])
            else:
                new_lines.append(line)
        note = '\n'.join(new_lines)

    # 3. Random typos (0-3 per note via adjacent-char swap/drop/double)
    num_typos = random.choices([0, 1, 2, 3], weights=[40, 35, 20, 5], k=1)[0]
    if num_typos > 0:
        note = _introduce_typos(note, num_typos)

    # 4. Word merge (8% chance)
    if "word_merge" in quirks or random.random() < 0.08:
        note = _maybe_merge_words(note)

    # 5. Trailing whitespace (15% chance per line)
    lines = note.split('\n')
    new_lines = []
    for line in lines:
        if random.random() < 0.15:
            spaces = random.randint(1, 3)
            new_lines.append(line + ' ' * spaces)
        else:
            new_lines.append(line)
    note = '\n'.join(new_lines)

    # 6. Global Punctuation & Dollar Sign Chaos (Make $, . and , rare)
    def repl_dollar(m):
        amt = m.group(1)
        r = random.random()
        if r < 0.35: return amt
        elif r < 0.6: return f"{amt} bucks"
        elif r < 0.75: return f"{amt} dollars"
        return m.group(0) # Keep $ 25% of the time

    note = re.sub(r"\$(\d+)", repl_dollar, note)

    lines = note.split('\n')
    new_lines = []
    for line in lines:
        if random.random() < 0.65:
            # Safely strip commas not surrounded by digits (e.g. keep 1,000)
            line = re.sub(r'(?<!\d),(?!\d)', ' ', line)
            line = line.replace(' ,', ' ').replace(', ', ' ')
        
        if random.random() < 0.65:
            # Safely strip periods at the end of words/sentences (protects emails, urls, decimals)
            line = re.sub(r'\.(\s+|$)', r'\1', line)
            
        new_lines.append(line)
        
    note = '\n'.join(new_lines)
    # Collapse double spaces that might be caused by dropping punctuation
    note = re.sub(r' {2,}', ' ', note)

    return note.strip()


def _introduce_typos(text: str, count: int) -> str:
    """Introduce realistic typos. The same word always gets the same typo throughout
    the note — consistent imperfection, not random per-occurrence."""
    lines = text.split('\n')

    # Find all unique eligible words
    all_eligible = []
    for line_idx, line in enumerate(lines):
        words = line.split(' ')
        for word_idx, w in enumerate(words):
            if len(w) > 3 and w.isalpha() and not (line_idx == 0 and word_idx == 0):
                all_eligible.append((line_idx, word_idx, w.lower()))

    if len(all_eligible) < 2:
        return text

    # Build a word→typo_version map so each unique word gets one consistent typo
    word_typo_map: dict[str, str] = {}
    targets = random.sample(all_eligible, k=min(count, len(all_eligible)))

    for line_idx, word_idx, word_lower in targets:
        if word_lower in word_typo_map:
            continue  # already decided typo for this word
        word = lines[line_idx].split(' ')[word_idx]
        if len(word) < 4:
            continue
        typo_type = random.choice(["swap", "drop", "double"])
        char_idx = random.randint(1, len(word) - 2)
        char = word[char_idx].lower()
        if typo_type == "swap" and char in ADJACENT_KEYS:
            new_word = word[:char_idx] + random.choice(ADJACENT_KEYS[char]) + word[char_idx + 1:]
        elif typo_type == "drop":
            new_word = word[:char_idx] + word[char_idx + 1:]
        elif typo_type == "double":
            new_word = word[:char_idx] + word[char_idx] + word[char_idx:]
        else:
            continue
        word_typo_map[word_lower] = new_word

    # Apply typos — ALL occurrences of a chosen word get the same replacement
    for line_idx, line in enumerate(lines):
        words = line.split(' ')
        new_words = []
        for word_idx, w in enumerate(words):
            typo = word_typo_map.get(w.lower())
            if typo and not (line_idx == 0 and word_idx == 0):
                new_words.append(typo)
            else:
                new_words.append(w)
        lines[line_idx] = ' '.join(new_words)

    return '\n'.join(lines)


def _maybe_merge_words(text: str) -> str:
    """Merge two adjacent words together (like 'sisterout' in the sample)."""
    words = text.split()
    if len(words) < 4:
        return text

    # Find eligible merge points (skip title line)
    lines = text.split('\n')
    if len(lines) < 2:
        return text

    # Work on a random non-title line
    line_idx = random.randint(1, len(lines) - 1) if len(lines) > 1 else 0
    line_words = lines[line_idx].split()

    if len(line_words) < 3:
        return text

    # Pick merge point
    merge_idx = random.randint(0, len(line_words) - 2)
    w1 = line_words[merge_idx]
    w2 = line_words[merge_idx + 1]

    # Only merge if both words are reasonably short
    if len(w1) > 8 or len(w2) > 8 or not w1.isalpha() or not w2[-1:].isalpha():
        return text

    merged = w1.rstrip() + w2
    line_words[merge_idx] = merged
    line_words.pop(merge_idx + 1)
    lines[line_idx] = ' '.join(line_words)

    return '\n'.join(lines)


def _add_random_empty_lines(text: str) -> str:
    """Randomly insert blank lines between thoughts/lines for a chaotic look."""
    lines = text.split('\n')
    if len(lines) < 2:
        return text

    new_lines = []
    for i, line in enumerate(lines):
        new_lines.append(line)
        # 30% chance to add a blank line between lines, except at the end
        if i < len(lines) - 1 and line.strip() and random.random() < 0.3:
            new_lines.append("")

    return '\n'.join(new_lines)
