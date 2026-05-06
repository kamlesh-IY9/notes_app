"""Topics of Interest (TOI) Note Generator — Pass A: LLM-based.

Golden sample style:
  aero drag coefficient study
  range estimate off by 43% in cold weather testing.... cell voltage delta exceeding 30mv
  might b why is this happening? NVH measurements showing 22dB peak at 58 rpm...

  enzymology n fermentation
  koji fermentation for dryaging beef.... aspergillus oryzae produces proteases that break
  down musclefiber into glutamates. need keep humidity at 80% n temp at 40f exactly...

Rules encoded:
- Person writing notes WHILE listening to expert/lecture — NOT copying an article
- Technical numbers (sometimes slightly off/approximate — realistic)
- At least one personal reaction per note (iirc, confused on this, need verify, hmm, etc.)
- Jargon + casual shorthand mixed together
- Title = specific technical topic name
- FAIL: recipes, safety tips, celebrity gossip, "according to researchers", article-copy style
"""

import logging
import random
import re
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent / "config"

_us_config: dict | None = None
_india_config: dict | None = None


def _load_config(language: str) -> dict:
    global _us_config, _india_config
    if language == "hindi":
        if _india_config is None:
            with open(CONFIG_DIR / "india_toi_topics.yaml") as f:
                _india_config = yaml.safe_load(f)
        return _india_config
    else:
        if _us_config is None:
            with open(CONFIG_DIR / "toi_topics.yaml") as f:
                _us_config = yaml.safe_load(f)
        return _us_config


BANNED_AI_VOCAB = [
    "delve", "tapestry", "testament", "orchestrate", "vibrant", "holistic",
    "seamless", "comprehensive", "robust", "leverage", "utilize",
    "whilst", "albeit", "moreover", "furthermore", "nonetheless", "consequently",
    "synergy", "paradigm", "harness", "navigate", "unlock", "empower",
    "multifaceted", "nuanced", "foster", "cultivate", "in conclusion",
    "crucial", "essential", "incredibly", "significantly",
    "it is worth noting", "it should be noted", "this is important",
]

# TOI-specific abbreviations
TOI_ABBREV_POOL = [
    "n", "abt", "bc", "iirc", "tbh", "ngl", "fr", "rn", "idk", "kinda",
    "prolly", "tho", "hmm", "smth", "r", "b", "4", "w/", "w/o", "vs",
    "eg", "ie", "etc", "approx", "rly", "def", "lol", "btw", "fyi",
]

# Personal reaction phrases
REACTION_POOL = [
    "is this normal??",
    "confused on this part",
    "need verify",
    "iirc",
    "dont quote me but",
    "might b wrong",
    "need recheck",
    "hmm",
    "from the session today",
    "wait no",
    "actually",
    "check this",
    "TODO look into this more",
    "hard to tell",
    "not sure tho",
    "need double check",
    "pretty sure abt this",
    "might be off here",
    "gotta look this up",
    "ok actually",
    "compare with last time",
    "from the meetup talk",
    "need confirm",
    "seems off",
    "or smth like that",
]

# Filler phrases to inject mid-note
FILLER_POOL = [
    "speaking of whch",
    "also",
    "oh n",
    "and then",
    "which reminds me",
    "note to self",
    "similar to last time",
    "might b why",
    "then again",
    "on top of that",
]


def _sample_abbrevs(n: int = 3) -> str:
    return ", ".join(random.sample(TOI_ABBREV_POOL, k=min(n, len(TOI_ABBREV_POOL))))


def _sample_reactions(n: int = 2) -> list[str]:
    return random.sample(REACTION_POOL, k=min(n, len(REACTION_POOL)))


def _sample_topic(config: dict) -> tuple[str, str, str]:
    """Returns (category_id, topic_name, category_label_for_prompt)."""
    cats = config["toi_categories"]
    weights = [c["weight"] for c in cats]
    chosen = random.choices(cats, weights=weights, k=1)[0]
    topic = random.choice(chosen["topic_names"])
    return chosen["id"], topic, chosen["id"].replace("_", " ")


def build_toi_prompt(
    category_id: str,
    topic_name: str,
    persona: dict,
    language: str = "english",
) -> tuple[str, str]:
    """Build system + user prompts for TOI note generation."""
    abbrevs = _sample_abbrevs(3)
    reactions = _sample_reactions(2)
    reaction_examples = " / ".join(f'"{r}"' for r in reactions)
    filler = random.choice(FILLER_POOL)

    if language == "hindi":
        locale_rules = (
            "- Topic must be relevant to India (cricket, UPSC, Nifty/NSE, Indian engineering, "
            "Bollywood music, Indian agriculture, Ayurveda, etc.)\n"
            "- If you mention money, use Indian format: ₹ or Rs, lakhs/crores (NOT millions/billions)\n"
            "- Number system: 1,00,000 not 100,000\n"
            "- Measurements: km, kg, liter, not miles/pounds\n"
            "- Indian English shorthand is fine: 'n' for and, 'r' for are, 'b' for be"
        )
    else:
        locale_rules = (
            "- STRICTLY US English. No 'whilst', 'colour', 'cheers'.\n"
            "- US measurements: mph, lbs, Fahrenheit, miles\n"
            "- US references: American context, American institutions"
        )

    system_prompt = f"""You write authentic personal phone notes taken during or right after a technical session, expert talk, workshop, or lecture.

THIS IS NOT AN ARTICLE. This is someone typing notes fast on their phone while an expert explains something.

CRITICAL STYLE RULES:
- Title line = specific technical topic (e.g. "aero drag coefficient study", "SiC inverter efficiency")
- 3 to 7 lines after the title, 25-80 words total
- Include at least ONE specific number or measurement — make it slightly off or approximate (realistic: "43%" not "40%", "22dB" not "20dB")
- Include at least ONE personal reaction like {reaction_examples}
- Mix technical jargon with casual shorthand: use {abbrevs}
- Use "..." for trailing thoughts, word merges ("fastcharging", "cellvoltage"), casual cuts ("n" for and)
- Middle of thoughts: add "{filler}" to feel like real note-taking flow
- NO perfect grammar, NO bullet list of clean facts, NO "according to researchers", NO "studies show"
- NO recipes (no "1 cup", "tablespoon", "step 1"), NO safety tips ("always remember to", "stay safe")
- NO celebrity gossip, NO "researchers found", NO article-copy language
- All lowercase mostly. Some technical terms can be capitalized (NVH, CAPE, RSI)

{locale_rules}

Output ONLY the note. Title first, then body lines."""

    occ = persona.get("occupation", "enthusiast")
    state = persona.get("state", "US")
    age = persona.get("age", random.randint(22, 45))

    user_prompt = (
        f"{age}yo {occ} from {state}. "
        f"Write personal phone notes for topic: '{topic_name}'. "
        f"Category: {category_id.replace('_', ' ')}. "
        f"Write like someone taking notes during an expert talk — "
        f"specific numbers, personal reactions, jargon + casual mixed. NOT an article."
    )

    return system_prompt, user_prompt


async def generate_toi_note(
    llm_clients,
    persona: dict,
    language: str = "english",
) -> tuple[str, dict]:
    """Generate one TOI note. Returns (note_text, metadata)."""
    config = _load_config(language)
    category_id, topic_name, category_label = _sample_topic(config)

    system_prompt, user_prompt = build_toi_prompt(
        category_id, topic_name, persona, language
    )

    temperature = round(random.uniform(0.95, 1.20), 2)

    note = await llm_clients.generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_tokens=250,
        provider="auto",
    )

    note = note.strip().strip('"').strip("'")
    if note.startswith("```"):
        note = note.split("```")[1] if "```" in note[3:] else note[3:]
        note = note.strip()

    # Hard cap at 9 lines
    lines = [l.strip() for l in note.split("\n") if l.strip()]
    note = "\n".join(lines[:9])

    metadata = {
        "category": category_id,
        "topic_name": topic_name,
    }
    return note, metadata


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_NUMBER_RE = re.compile(r"\d+\.?\d*\s*(%|dB|ms|rpm|kHz|Hz|MB|GB|TB|km|kg|liter|mph|fps|bps|V|W|kW|MW|₹|Rs|lakh|crore)")
_HAS_NUMBER_RE = re.compile(r"\b\d+\b")

_RECIPE_RE = re.compile(
    r"\b(\d+\s*(cup|tablespoon|teaspoon|tbsp|tsp|gram|oz|pound|lb)\b|step\s+\d+|preheat\s+oven)",
    re.IGNORECASE,
)
_SAFETY_TIPS_RE = re.compile(
    r"\b(always\s+remember\s+to|in\s+case\s+of\s+emergency|stay\s+safe|never\s+forget\s+to|"
    r"for\s+your\s+safety|survival\s+tip|safety\s+tip)\b",
    re.IGNORECASE,
)
_ARTICLE_COPY_RE = re.compile(
    r"\b(according\s+to|researchers?\s+(found|say|suggest|show)|"
    r"studies?\s+(show|found|suggest)|it\s+has\s+been\s+(found|shown|reported)|"
    r"experts?\s+(say|believe|recommend)|the\s+study\s+(shows|found))\b",
    re.IGNORECASE,
)

_REACTION_KEYWORDS = [
    "iirc", "hmm", "confused", "verify", "recheck", "not sure", "dont quote",
    "might b", "hard to tell", "wait no", "actually", "gotta", "check this",
    "todo", "seems off", "need to look", "from the", "session",
]


def validate_toi_note(note: str, language: str = "english") -> list[dict]:
    """Return list of failed checks. Empty list = passed."""
    failures = []
    lines = [l.strip() for l in note.split("\n") if l.strip()]
    word_count = len(note.split())

    # Word count: 15-110
    if not (15 <= word_count <= 110):
        failures.append({"name": "word_count", "passed": False,
                         "detail": f"Word count: {word_count} (need 15-110)"})

    # Line count: 2-9
    if not (2 <= len(lines) <= 9):
        failures.append({"name": "line_count", "passed": False,
                         "detail": f"Lines: {len(lines)} (need 2-9)"})

    # Must have at least one number
    if not _HAS_NUMBER_RE.search(note):
        failures.append({"name": "has_technical_content", "passed": False,
                         "detail": "No numbers found — needs technical specifics"})

    # Must have at least one personal reaction
    note_lower = note.lower()
    has_reaction = any(kw in note_lower for kw in _REACTION_KEYWORDS)
    if not has_reaction:
        failures.append({"name": "has_personal_voice", "passed": False,
                         "detail": "No personal reaction found (iirc, hmm, confused, etc.)"})

    # Recipe format check
    if _RECIPE_RE.search(note):
        failures.append({"name": "no_recipe_format", "passed": False,
                         "detail": "Contains recipe-style format (rejected category)"})

    # Safety tips check
    if _SAFETY_TIPS_RE.search(note):
        failures.append({"name": "no_safety_tips", "passed": False,
                         "detail": "Contains safety tips (rejected category)"})

    # Article copy check
    if _ARTICLE_COPY_RE.search(note):
        failures.append({"name": "no_article_copy", "passed": False,
                         "detail": "Contains article-copy phrasing (researchers found, according to, etc.)"})

    # AI vocab check
    for word in BANNED_AI_VOCAB:
        if word in note_lower:
            failures.append({"name": "no_ai_vocab", "passed": False,
                             "detail": f"Banned AI word: '{word}'"})
            break

    return failures
