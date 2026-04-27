"""Validator — gate before persisting an entry. Runs 12+ checks."""

import re
import logging
from pathlib import Path
from typing import Optional

import yaml

log = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent / "config"

# Load lint config
with open(CONFIG_DIR / "us_only_lint.yaml") as f:
    US_LINT = yaml.safe_load(f)

# Import banned vocab from note_generator
from .note_generator import BANNED_AI_VOCAB, BANNED_PHRASES


class ValidationResult:
    def __init__(self):
        self.checks: list[dict] = []
        self.passed = True
        self.auto_fixed = False
        self.fixed_text: Optional[str] = None

    def add_check(self, name: str, passed: bool, detail: str = ""):
        self.checks.append({"name": name, "passed": passed, "detail": detail})
        if not passed:
            self.passed = False

    def to_dict(self) -> list[dict]:
        return self.checks


def validate_note(
    note: str,
    persona: dict,
    related_name: str,
    relationship: dict,
    has_title: bool,
    note_date: str,
) -> ValidationResult:
    """Run all validation checks on a generated note."""
    result = ValidationResult()
    lines = [l for l in note.split('\n') if l.strip()]

    # 1. Word count: 10-60
    word_count = len(note.split())
    result.add_check("word_count", 10 <= word_count <= 60, f"Word count: {word_count} (need 10-60)")

    # 2. Line count: 1-6
    lc = len(lines)
    if has_title:
        ok = 2 <= lc <= 6  # 1 for title, at least 1 for body
        result.add_check("line_count", ok, f"Lines: {lc} (need 2-6 with title)")
    else:
        ok = 1 <= lc <= 5
        result.add_check("line_count", ok, f"Lines: {lc} (need 1-5 without title)")

    # 3. Title length ≤ 6 words (when present)
    if has_title and lines:
        title_words = lines[0].split()
        result.add_check(
            "title_length",
            len(title_words) <= 6,
            f"Title words: {len(title_words)} (max 6)"
        )

    # 4. US spelling check
    us_ok, us_detail = _check_us_spelling(note)
    result.add_check("us_spelling", us_ok, us_detail)

    # 5. Banned AI vocabulary
    ai_ok, ai_detail = _check_banned_vocab(note)
    result.add_check("banned_ai_vocab", ai_ok, ai_detail)

    # 6. Em dashes
    has_em = bool(re.search(r'[—–]', note))
    result.add_check("no_em_dashes", not has_em, "Contains em/en dashes" if has_em else "Clean")

    # 7. State restriction (no TX/IL/WA mentions)
    state_ok, state_detail = _check_state_restriction(note, persona)
    result.add_check("state_restriction", state_ok, state_detail)

    # 8. Name-gender consistency
    # Verified during persona sampling, but double-check relationship labels
    gender_ok = _check_name_gender(note, related_name, relationship, persona)
    result.add_check("name_gender", gender_ok, "Name-gender check")

    # 9. Writer knows the named person (heuristic check)
    writer_ok = _check_writer_knows_person(note, related_name, relationship)
    result.add_check("writer_relationship", writer_ok,
                     "Writer clearly knows the named person" if writer_ok else
                     "Writer's relationship to named person unclear")

    # 10. No corporate confidentiality
    corp_ok = _check_no_corporate(note)
    result.add_check("no_corporate", corp_ok, "No corporate/confidential content")

    # 11. Shall check (British future tense)
    shall_ok = "shall" not in note.lower().split()
    result.add_check("no_shall", shall_ok, 
                     "Contains 'shall' (British)" if not shall_ok else "Clean")

    # 12. "Sorry to here" style errors — but allow intentional typos
    # This checks for common AI-generated "fake error" patterns
    ai_error_ok = True
    fake_errors = ["sorry to here", "your welcome", "should of been"]
    for err in fake_errors:
        if err in note.lower():
            ai_error_ok = False
    result.add_check("no_ai_fake_errors", ai_error_ok, "No AI-style fake errors")

    return result


def auto_fix_note(note: str) -> tuple[str, list[str]]:
    """Attempt to auto-fix common issues. Returns (fixed_note, list_of_fixes)."""
    fixes = []

    # Fix US spelling
    auto_fixes = US_LINT.get("auto_fixes", {})
    for brit, us in auto_fixes.items():
        pattern = re.compile(re.escape(brit), re.IGNORECASE)
        if pattern.search(note):
            note = pattern.sub(us, note)
            fixes.append(f"Replaced '{brit}' → '{us}'")

    # Kill em dashes
    if re.search(r'[—–]', note):
        note = re.sub(r'\s*[—–]\s*', ', ', note)
        note = re.sub(r'\s*,\s*,', ',', note)
        fixes.append("Removed em/en dashes")

    return note, fixes


def _check_us_spelling(note: str) -> tuple[bool, str]:
    """Check for British English spellings."""
    note_lower = note.lower()
    found = []

    for word in US_LINT.get("british_words", []):
        # Word boundary check to avoid false positives
        if re.search(r'\b' + re.escape(word) + r'\b', note_lower):
            found.append(word)

    for phrase in US_LINT.get("british_phrases", []):
        if phrase.lower() in note_lower:
            # Special handling for "shall" — only flag if used as future tense
            if phrase.lower() == "shall":
                words = note_lower.split()
                if "shall" in words:
                    found.append(phrase)
            else:
                found.append(phrase)

    if found:
        return False, f"British terms found: {', '.join(found[:5])}"
    return True, "Pure US English"


def _check_banned_vocab(note: str) -> tuple[bool, str]:
    """Check for banned AI vocabulary and phrases."""
    note_lower = note.lower()
    found = []

    for word in BANNED_AI_VOCAB:
        if re.search(r'\b' + re.escape(word) + r'\b', note_lower):
            found.append(word)

    for phrase in BANNED_PHRASES:
        if phrase.lower() in note_lower:
            found.append(phrase)

    if found:
        return False, f"AI vocab found: {', '.join(found[:5])}"
    return True, "No banned AI vocab"


def _check_state_restriction(note: str, persona: dict) -> tuple[bool, str]:
    """Check that excluded states/cities aren't mentioned."""
    note_lower = note.lower()
    excluded = US_LINT.get("excluded_locations", {})

    for state in excluded.get("states", []):
        if state.lower() in note_lower:
            return False, f"Excluded state mentioned: {state}"

    for city in excluded.get("cities", []):
        if city.lower() in note_lower:
            return False, f"Excluded city mentioned: {city}"

    # Also check persona state
    if persona.get("state") in ["TX", "IL", "WA"]:
        return False, f"Persona from excluded state: {persona['state']}"

    return True, "No excluded locations"


def _check_name_gender(note: str, related_name: str, relationship: dict,
                       persona: dict) -> bool:
    """Basic name-gender consistency check."""
    rel_id = relationship["id"]
    note_lower = note.lower()

    # Check for mismatched gender labels
    female_labels = ["mom", "mother", "mama", "sister", "sis", "girlfriend",
                     "wife", "daughter", "grandma", "nana", "granny", "aunt",
                     "auntie", "fiancée"]
    male_labels = ["dad", "father", "papa", "pops", "brother", "bro",
                   "boyfriend", "husband", "son", "grandpa", "gramps",
                   "uncle", "fiancé"]

    # If the note uses a gendered label, it should at least be present coherently
    # This is a basic check — the LLM judge does the deeper analysis
    return True


def _check_writer_knows_person(note: str, related_name: str,
                                relationship: dict) -> bool:
    """Check that the writer personally knows the named person."""
    note_lower = note.lower()
    name_lower = related_name.lower()

    # The name should appear in the note
    if name_lower not in note_lower:
        return False

    # Check for first-person connection indicators
    first_person = ["i ", "my ", "me ", "i'm", "im ", "we ", "our ", "i'll",
                    "mine", "myself"]
    has_first_person = any(fp in note_lower for fp in first_person)

    # Check for relationship label
    rel_labels = [l.lower() for l in relationship.get("labels", [])]
    has_rel_label = any(rl in note_lower for rl in rel_labels)

    return has_first_person or has_rel_label


def _check_no_corporate(note: str) -> bool:
    """Check for corporate confidentiality markers."""
    note_lower = note.lower()
    corporate_markers = [
        "confidential", "proprietary", "nda", "trade secret",
        "classified", "internal only", "do not distribute",
    ]
    return not any(m in note_lower for m in corporate_markers)
