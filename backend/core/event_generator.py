"""Event Note Generator — Pass A: LLM-based event note generation.

Golden sample style:
  ai hackathon coming up May 14 in Raleigh NC at NC State Hunt Library starts 9am
  need to:  laptop  charger  dataset

  Board Meeting
  Sept 19 8:00 AM Atlanta, GA (HQ Building) Room 402

  quick vegas trip lol Aug 2
  flight 4pm from San Diego CA… staying MGM Grand Las Vegas NV

Rules encoded:
- Casual, varied structure — NOT "Title\nDate, Time\nCity, State\n- items"
- Date always present (2021+), location casual
- Short (1-5 lines), phone-typing feel
- No TX/IL/WA for English US; Indian cities for Hindi
"""

import logging
import random
import re
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent / "config"

# Lazy-loaded config
_us_config: dict | None = None
_india_config: dict | None = None
_arabic_config: dict | None = None


def _load_config(language: str) -> dict:
    global _us_config, _india_config, _arabic_config
    if language == "hindi":
        if _india_config is None:
            with open(CONFIG_DIR / "india_event_topics.yaml") as f:
                _india_config = yaml.safe_load(f)
        return _india_config
    elif language == "arabic":
        if _arabic_config is None:
            with open(CONFIG_DIR / "arabic_event_topics.yaml") as f:
                _arabic_config = yaml.safe_load(f)
        return _arabic_config
    else:
        if _us_config is None:
            with open(CONFIG_DIR / "event_topics.yaml") as f:
                _us_config = yaml.safe_load(f)
        return _us_config


# Banned AI vocabulary — copy from note_generator for consistency
BANNED_AI_VOCAB = [
    "delve", "tapestry", "testament", "orchestrate", "vibrant", "holistic",
    "seamless", "comprehensive", "robust", "leverage", "utilize",
    "whilst", "albeit", "moreover", "furthermore", "nonetheless", "consequently",
    "synergy", "paradigm", "harness", "navigate", "unlock", "empower",
    "multifaceted", "nuanced", "foster", "cultivate", "in conclusion",
    "crucial", "essential", "incredibly", "significantly",
]

# Event-specific abbrev pool
EVENT_ABBREV_POOL = [
    "rn", "tbh", "ngl", "idk", "btw", "bc", "lol", "lmao", "smh", "fr",
    "asap", "kinda", "prolly", "gonna", "wanna", "gotta", "atm", "tmrw",
    "wknd", "appt", "est", "rsvp", "hmu", "brb", "ofc", "thx", "bday",
]

# Structure starters — sampled 4 per call to show LLM the variety
EVENT_START_POOL = [
    "quick [event_type] note",
    "[event_type] coming up",
    "dont forget [event_type]",
    "heads up —",
    "reminder:",
    "just a note abt",
    "[event_type] is",
    "ok so",
    "almost forgot —",
    "[event_type] happening",
    "need to plan for",
    "marking down",
    "saving this —",
    "fyi [event_type]",
    "[event_type] lol",
    "logging [event_type]",
]

# Authentic mobile note typos for events
EVENT_TYPO_POOL = [
    "tmrw", "tonite", "recieve", "definately", "Wednsday", "Thurday",
    "calander", "schedul", "cofirmation", "accomodation", "seperate",
    "ther", "alredy", "probaly", "wether",
]


def _sample_abbrevs(n: int = 3) -> str:
    return ", ".join(random.sample(EVENT_ABBREV_POOL, k=min(n, len(EVENT_ABBREV_POOL))))


def _sample_starts(event_label: str, n: int = 4) -> str:
    chosen = random.sample(EVENT_START_POOL, k=min(n, len(EVENT_START_POOL)))
    filled = [s.replace("[event_type]", event_label) for s in chosen]
    return "\n  ".join(f'"{s}..."' for s in filled)


def _sample_typos(n: int = 2) -> str:
    return ", ".join(random.sample(EVENT_TYPO_POOL, k=min(n, len(EVENT_TYPO_POOL))))


def _sample_event(config: dict) -> tuple[str, str]:
    """Weighted sample of (event_type_id, event_label)."""
    types = config["event_types"]
    weights = [t["weight"] for t in types]
    chosen = random.choices(types, weights=weights, k=1)[0]
    label = random.choice(chosen["labels"])
    return chosen["id"], label


def _sample_location(config: dict, event_type_id: str, language: str) -> str:
    """Return a casual location string appropriate for the event type."""
    if language == "hindi":
        cities = config["india_cities"]
        all_cities = cities.get("metro", []) + cities.get("tier2", [])
        city = random.choice(all_cities)
        venues = config["venues"]
        if event_type_id == "work_meeting":
            venue = random.choice(venues["work"])
        elif event_type_id == "festival_religious":
            venue = random.choice(venues["religious"])
        elif event_type_id == "travel_outing":
            venue = random.choice(venues["outdoor"])
        else:
            venue = random.choice(venues["social"])
        # 60% city + venue, 40% just city
        if random.random() < 0.6:
            return f"{city} at {venue}"
        return city
    elif language == "arabic":
        arab_cities = config["arab_cities"]
        # Pick region: 70% Gulf, 20% Levant/Egypt, 10% North Africa
        region_roll = random.random()
        if region_roll < 0.70:
            city = random.choice(arab_cities.get("gulf", ["Dubai"]))
        elif region_roll < 0.90:
            city = random.choice(arab_cities.get("levant_egypt", ["Cairo"]))
        else:
            city = random.choice(arab_cities.get("north_africa", ["Casablanca"]))
        venues = config["venues"]
        if event_type_id == "work_meeting":
            venue_pool = venues.get("work", [])
        elif event_type_id == "religious_celebration":
            venue_pool = venues.get("religious", [])
        elif event_type_id == "travel_outing":
            venue_pool = venues.get("outdoor", [])
        elif event_type_id == "personal_appointment":
            venue_pool = venues.get("personal", [])
        else:
            venue_pool = venues.get("social", [])
        # 55% city + venue, 45% just city
        if random.random() < 0.55 and venue_pool:
            venue = random.choice(venue_pool)
            return f"{city} at {venue}"
        return city
    else:
        regions = config["us_cities"]
        region = random.choice(list(regions.keys()))
        city = random.choice(regions[region])
        venues = config["venues"]
        if event_type_id in ("work_meeting", "learning_event"):
            venue_pool = venues.get("work", []) + venues.get("learning", [])
        elif event_type_id == "travel_outing":
            venue_pool = venues.get("outdoor", [])
        else:
            venue_pool = venues.get("social", [])
        # 55% city + venue, 45% just city
        if random.random() < 0.55 and venue_pool:
            venue = random.choice(venue_pool)
            return f"{city} at {venue}"
        return city


def _sample_date_fragment(language: str) -> str:
    """Return a casual date string fragment (2021+)."""
    months_full = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sept", "Oct", "Nov", "Dec",
    ]
    month = random.choice(months_full)
    day = random.randint(1, 28)

    # 30% include year (2021-2026), 70% just month+day
    if random.random() < 0.3:
        year = random.randint(2021, 2026)
        return f"{month} {day}, {year}"
    return f"{month} {day}"


def _sample_time_fragment() -> str | None:
    """Return a casual time string or None (50% chance)."""
    if random.random() < 0.5:
        return None
    hours = [7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8]
    h = random.choice(hours)
    # 60% round hour, 40% with minutes
    if random.random() < 0.6:
        ampm = "AM" if h <= 12 and h >= 7 and random.random() < 0.5 else "pm"
        return f"{h}{ampm}"
    mins = random.choice([15, 30, 45])
    ampm = "AM" if h <= 12 and h >= 7 and random.random() < 0.4 else "pm"
    return f"{h}:{mins:02d}{ampm}"


def build_event_prompt(
    event_type_id: str,
    event_label: str,
    location: str,
    date_fragment: str,
    time_fragment: str | None,
    persona: dict,
    language: str = "english",
) -> tuple[str, str]:
    """Build system + user prompts for event note generation."""
    example_starts = _sample_starts(event_label)
    abbrevs = _sample_abbrevs(3)
    typos = _sample_typos(2)

    time_hint = f" at {time_fragment}" if time_fragment else ""
    location_hint = location

    if language == "hindi":
        locale_rules = (
            "- Location must be an Indian city or venue (Mumbai, Pune, Delhi, Bangalore, etc.)\n"
            "- Use Indian English and Indian context (autorickshaw, chai, society, colony, etc.)\n"
            "- If prices appear, use Indian amounts (₹500, 2000 rupees, Rs 1500)\n"
            "- Dates in natural format: 'March 15' or '15 March' or 'Mar 15'"
        )
        country_note = "Indian"
    elif language == "arabic":
        locale_rules = (
            "- Location must be an Arab city (Dubai, Riyadh, Abu Dhabi, Cairo, Doha, etc.)\n"
            "- Use Gulf/Arab context (souq, diwaniya, iftar, Eid, iqama, Salik, etc.)\n"
            "- Currency: AED, SAR, KWD, EGP — NOT dollars\n"
            "- Dates in natural format: 'March 15' or '15 March'\n"
            "- NEVER mention Western countries as the location\n"
            "- STRICTLY no 'whilst', 'cheers', 'mate'"
        )
        country_note = "Arab"
    else:
        locale_rules = (
            "- Location must be a real US city/state (casual format: 'Orlando FL', 'San Jose CA')\n"
            "- NEVER use Texas, Illinois (as residence), Washington state (as residence)\n"
            "- NEVER write a full formal address like 'Embassy Suites, City, State'\n"
            "- NEVER mention globally famous landmarks (Eiffel Tower, Times Square, Grand Canyon)\n"
            "- STRICTLY US English — no 'whilst', 'colour', 'cheers', 'mate'"
        )
        country_note = "US"

    system_prompt = f"""You write very short phone calendar notes. These are real people's quick event reminders typed on a mobile phone.

CRITICAL RULES:
- 1 to 5 lines MAXIMUM. NEVER longer.
- Date is REQUIRED. Use: {date_fragment}{time_hint}
- Location is REQUIRED. Use: {location_hint}
- Write like a real person typing fast on their phone — NOT like a formatted calendar entry
- NO rigid template. This is WRONG: "Event Name\\nDate, Time\\nCity, State\\n- bullet items"
- VARY the structure every time. Examples of good openings:
  {example_starts}
- The title (if any) should be casual: "quick vegas trip lol", "alex bday dinner", "board mtg" — NOT formal
- Casual shortcuts: {abbrevs}
- Optional: 1-2 action items at the bottom ("book flight", "bring gift", "check registration")
- 1 small typo OK: {typos}
- All lowercase except proper nouns. Drop apostrophes (dont, cant, wont)
- Use ... for trailing off sometimes
- NO em dashes, NO semicolons, NO formal bullet points

{locale_rules}

Output ONLY the note lines. Nothing else."""

    # Determine persona description
    occ = persona.get("occupation", "professional")
    state_or_city = persona.get("state", country_note)
    age = persona.get("age", random.randint(22, 45))

    user_prompt = (
        f"{age}yo {country_note} person, {occ} from {state_or_city}. "
        f"Write a quick phone note reminding themselves about: {event_label}. "
        f"Event is on {date_fragment}{time_hint} in/at {location_hint}. "
        f"Make it feel like a real casual mobile note — varied structure, not a template."
    )

    return system_prompt, user_prompt


async def generate_event_note(
    llm_clients,
    persona: dict,
    language: str = "english",
) -> tuple[str, dict]:
    """Generate one event note. Returns (note_text, metadata)."""
    config = _load_config(language)
    event_type_id, event_label = _sample_event(config)
    location = _sample_location(config, event_type_id, language)
    date_fragment = _sample_date_fragment(language)
    time_fragment = _sample_time_fragment()

    system_prompt, user_prompt = build_event_prompt(
        event_type_id, event_label, location, date_fragment, time_fragment,
        persona, language
    )

    temperature = round(random.uniform(0.90, 1.15), 2)

    note = await llm_clients.generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_tokens=150,
        provider="auto",
    )

    note = note.strip().strip('"').strip("'")
    if note.startswith("```"):
        note = note.split("```")[1] if "```" in note[3:] else note[3:]
        note = note.strip()

    # Hard cap at 6 lines
    lines = [l.strip() for l in note.split("\n") if l.strip()]
    note = "\n".join(lines[:6])

    metadata = {
        "event_type": event_type_id,
        "event_label": event_label,
        "location": location,
        "date_fragment": date_fragment,
        "time_fragment": time_fragment or "",
    }
    return note, metadata


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

MONTHS = [
    "jan", "feb", "mar", "apr", "may", "jun",
    "jul", "aug", "sep", "oct", "nov", "dec",
    "january", "february", "march", "april", "june",
    "july", "august", "september", "october", "november", "december",
]

_MONTH_RE = re.compile("|".join(MONTHS), re.IGNORECASE)
_DATE_RE = re.compile(r"\b\d{1,2}[\/\-]\d{1,2}|\b\d{4}\b|\b\d{1,2}(st|nd|rd|th)\b", re.IGNORECASE)
_PRE2021_YEAR_RE = re.compile(r"\b(201[0-9]|200[0-9]|19\d{2})\b")

# Banned US states for English notes
_BANNED_STATE_PATTERNS = re.compile(
    r"\b(Texas|TX|Illinois|IL|Washington\s+state|Washington\s+WA|,\s*WA\b|,\s*IL\b|,\s*TX\b)\b",
    re.IGNORECASE,
)

# Globally banned landmarks
_BANNED_LANDMARKS = re.compile(
    r"\b(Eiffel\s+Tower|Taj\s+Mahal|Big\s+Ben|Times\s+Square|Hollywood\s+sign|"
    r"Grand\s+Canyon|Niagara\s+Falls|Golden\s+Gate|Statue\s+of\s+Liberty)\b",
    re.IGNORECASE,
)

# Template pattern detection — rigid "line1\nDate line\nCity, State line\n- items"
_TEMPLATE_LINE_RE = re.compile(
    r"^[-•*]\s+\w",  # bullet-point line
)


def validate_event_note(note: str, language: str = "english") -> list[dict]:
    """Return list of failed checks. Empty list = passed."""
    failures = []
    lines = [l.strip() for l in note.split("\n") if l.strip()]
    word_count = len(note.split())

    # Word count
    if not (5 <= word_count <= 70):
        failures.append({"name": "word_count", "passed": False,
                         "detail": f"Word count: {word_count} (need 5-70)"})

    # Line count
    if not (1 <= len(lines) <= 7):
        failures.append({"name": "line_count", "passed": False,
                         "detail": f"Lines: {len(lines)} (need 1-7)"})

    # Must contain a date reference
    has_date = bool(_MONTH_RE.search(note)) or bool(_DATE_RE.search(note))
    if not has_date:
        failures.append({"name": "has_date", "passed": False,
                         "detail": "No date reference found"})

    # Pre-2021 year check
    pre2021 = _PRE2021_YEAR_RE.search(note)
    if pre2021:
        failures.append({"name": "no_pre_2021", "passed": False,
                         "detail": f"Pre-2021 year: {pre2021.group()}"})

    # English-only checks
    if language not in ("hindi", "arabic"):
        if _BANNED_STATE_PATTERNS.search(note):
            failures.append({"name": "no_banned_states", "passed": False,
                             "detail": "Contains TX/IL/WA (banned states)"})

    # Globally banned landmarks
    if _BANNED_LANDMARKS.search(note):
        failures.append({"name": "no_banned_landmarks", "passed": False,
                         "detail": "Contains globally famous landmark"})

    # Template pattern: more than 2 bullet lines = likely template
    bullet_lines = sum(1 for l in lines if _TEMPLATE_LINE_RE.match(l))
    if bullet_lines >= 3:
        failures.append({"name": "no_template_pattern", "passed": False,
                         "detail": f"Too many bullet lines ({bullet_lines}) — looks like a template"})

    # AI vocab check
    note_lower = note.lower()
    for word in BANNED_AI_VOCAB:
        if word in note_lower:
            failures.append({"name": "no_ai_vocab", "passed": False,
                             "detail": f"Banned AI word: '{word}'"})
            break

    return failures
