"""Note Generator — Pass A: LLM-based note generation with persona inhabitation."""

import random
import logging
import re

log = logging.getLogger(__name__)

# Banned AI vocabulary — must NEVER appear in generated notes
BANNED_AI_VOCAB = [
    "delve", "leverage", "transformative", "seamless", "robust",
    "synergy", "best practices", "landscape", "paradigm",
    "harness", "navigate", "unlock", "empower", "streamline",
    "tapestry", "multifaceted", "nuanced", "foster", "cultivate",
    "utilize", "comprehensive", "albeit", "whilst",
    "furthermore", "moreover", "in conclusion", "additionally",
    "crucial", "essential", "incredibly", "significantly",
]

BANNED_PHRASES = [
    "brutal clarity", "lost the plot", "painfully clear", "blunt honesty",
    "with precision", "lived experience", "launching a new chapter",
    "the energy in the room", "laying the groundwork", "here's to",
    "will never be the same", "that promise becomes reality",
    "ends the era of", "the same tension", "keeping my hands dirty",
    "not only...but also", "here's a breakdown", "in the ever-evolving",
    "a testament to", "there is a specific kind of",
    "in today's", "when it comes to", "at the end of the day",
    "it's important to note", "one might argue", "it goes without saying",
]

# Pool of casual abbreviations / texting shortcuts. Per-call, we draw 3 random
# items so the prompt the LLM sees is never identical twice in a row — this
# breaks the lock-in where every note ended with "rn" / "ngl" / "tbh".
ABBREV_POOL = [
    "rn", "tbh", "ngl", "idk", "imo", "imho", "fyi", "btw", "bc", "cuz",
    "tho", "kinda", "prolly", "gonna", "wanna", "gotta", "yall", "lol",
    "lmao", "smh", "fr", "fr fr", "deadass", "lowkey", "highkey",
    "atm", "asap", "rly", "hella", "kinda", "sorta", "supp", "pls", "plz",
    "thx", "ty", "yw", "omw", "brb", "ttyl", "lmk", "np", "smth",
    "sumone", "abt", "btwn", "w/", "w/o", "irl", "ofc", "mfw", "idek",
]

# Pool of natural-looking misspellings. Per-call, we draw 3 random items so
# the LLM never sees "tomorrowis / ther / sisterout / alredy / whn" together
# again. The injection function provides examples; the actual typo insertion
# happens algorithmically in jitter.py.
TYPO_POOL = [
    "alredy", "ther", "tmrw", "tonite", "cuz", "definitly", "Febuary",
    "Wednsday", "becuz", "supposta", "shouldve", "couldve", "wouldve",
    "frined", "douments", "cearly", "roomate", "neighbor", "favrite",
    "addres", "probaly", "tomorow", "yesterdy", "eventho", "alot",
    "deff", "totes", "bday", "nite", "lite", "kno", "thier", "wether",
    "definately", "seperate", "recieve", "occured", "untill", "comming",
    "runing", "puting", "geting", "stoped", "writting", "begining",
    "diffrent", "managment", "embarass", "calender", "midnigt",
]


def _sample_abbrevs(n: int = 3) -> str:
    """Return a comma-separated string of n random abbreviations."""
    return ", ".join(random.sample(ABBREV_POOL, k=min(n, len(ABBREV_POOL))))


def _sample_typos(n: int = 3) -> str:
    """Return a comma-separated string of n random natural-looking misspellings."""
    return ", ".join(random.sample(TYPO_POOL, k=min(n, len(TYPO_POOL))))


# Gender mapping for relationship labels. Used to filter relationship["labels"]
# so that the picked label matches the related_gender we already chose for the
# related person. Without this, "lucia my dad" / "brother hazel" can slip
# through (female-only name + male label, or vice versa).
LABEL_GENDER = {
    # Parent
    "mom": "female", "mother": "female", "mama": "female",
    "dad": "male", "father": "male", "papa": "male", "pops": "male",
    # Sibling
    "sister": "female", "sis": "female",
    "brother": "male", "bro": "male",
    # Partner
    "boyfriend": "male", "girlfriend": "female",
    "husband": "male", "wife": "female",
    "fiancé": "male", "fiancée": "female",
    # Child
    "son": "male", "daughter": "female",
    # Grandparent
    "grandma": "female", "nana": "female", "granny": "female",
    "grandpa": "male", "gramps": "male",
    # Step-family
    "step-mom": "female", "stepmom": "female",
    "step-dad": "male", "stepdad": "male",
    "step-sister": "female", "step-sis": "female",
    "step-brother": "male", "step-bro": "male",
    "step-son": "male", "step-daughter": "female",
    # Grandkid
    "grandson": "male", "granddaughter": "female",
    # Service / family-friend gendered
    "godmother": "female", "godfather": "male",
    "uncle": "male", "uncle figure": "male",
    "aunt": "female", "auntie": "female", "aunt figure": "female",
    "cleaning lady": "female", "yard guy": "male", "lawn guy": "male",
    "dog dad i met at the park": "male", "the lady from the dog park": "female",
    "my kid's friend's mom": "female", "my kid's friend's dad": "male",
    # Everything else (partner, friend, spouse, neutral labels) → "any"
}


def _pick_gendered_label(labels: list[str], related_gender: str) -> str:
    """Pick a label from `labels` that matches `related_gender` if possible.

    Falls back to a random label only if no gendered label matches the gender
    (which happens for fully-neutral relationship pools like "friend" or
    "partner" — that's fine, those labels carry no gender signal).
    """
    if related_gender == "nonbinary":
        compatible = [l for l in labels if LABEL_GENDER.get(l) is None]
        return random.choice(compatible) if compatible else random.choice(labels)
    matching = [l for l in labels if LABEL_GENDER.get(l, "any") in (related_gender, "any")]
    return random.choice(matching) if matching else random.choice(labels)

def build_generation_prompt(
    persona: dict,
    relationship: dict,
    topic: dict,
    mood: str,
    related_name: str,
    has_title: bool,
    target_word_count: int,
    target_line_count: int,
    related_gender: str = "any",
) -> tuple[str, str]:
    """Build system + user prompts for Pass A note generation."""
    rel_label = _pick_gendered_label(relationship["labels"], related_gender)
    topic_label = random.choice(topic["labels"])
    quirk_instructions = _build_quirk_instructions(persona.get("voice_quirks", []))

    title_instruction = ""
    if has_title:
        title_instruction = "Start with a 1-3 word title on line 1, then a blank line, then the body."

    system_prompt = f"""You write very short phone notes. Each note has {target_line_count} lines. Each line = one thought. Choppy, natural, like real phone notes.

EXAMPLES:
{title_instruction}

{("pick up car" + chr(10) + chr(10)) if has_title else ""}gotta call the mechanic rn
uncle bob said he already paid for it
so making sure everything is good
i need my car tomorrow

need to remind mom
shes supposed to call the insurance guy
deal ends at midnight
dont forget this is imp

finance meeting with my boss
he is asking for the Q3 numbers today
i better finish the sheets rn
this is actually stressful

RULES:
- {target_word_count} words total, {target_line_count} lines MAX.
- One thought per line. Short fragments. NOT a story.
- DO NOT talk about catching up after 5 years, meeting old friends, or nostalgia. Make the note an IMPORTANT task, reminder, or work-related thought that involves the relationship.
- You MUST explicitly state the relationship. Example: 'my friend alex', 'uncle bob', 'mom', 'my boss'. DO NOT JUST SAY the name.
- {related_name} is your {rel_label}. Mention them AND the relationship naturally in the note.
- All lowercase. Drop apostrophes: dont, didnt, im, hes, shes, its, wasnt, wont
- Use ... at end of some lines for trailing off
- Use casual shortcuts naturally — pick from words like: {_sample_abbrevs(3)}
- Extreme lazy abbreviations are encouraged: tmrw, 2moro, appt, est, wknd
- 1-2 small typos OK — examples of the kind of natural misspellings: {_sample_typos(3)}
- Avoid perfect punctuation. Rarely use commas (,). Never use slashes (/) or backslashes (\).
- Sometimes drop periods at the end of lines, sometimes keep them. Do not be perfectly consistent.
- NO em dashes or semicolons.
- Emotional and messy, not polished
- If you include a phone number, NEVER use "555" patterns. Use a realistic 10-digit number. Mix it up with hyphens, dots, or spaces.
- If you include a dollar amount, frequently omit the $ sign or use words like 'bucks' or 'dollars'.
- If you include an email address, make it look realistic.
{quirk_instructions}

Output ONLY the note lines."""

    user_prompt = f"""{persona['age']}yo {persona['gender']}, {persona['occupation']} from {persona['state']}. Topic: {topic_label}. {related_name} is your {rel_label}. Mood: {mood}. Include one concrete detail."""

    return system_prompt, user_prompt


def _build_quirk_instructions(quirks: list[str]) -> str:
    """Convert quirk IDs into writing instructions."""
    if not quirks:
        return ""

    instructions = []
    quirk_map = {
        "lowercase_starts": "dont capitalize anything",
        "drop_apostrophes": "skip apostrophes (dont, cant, wont, im)",
        "use_ampersand": "use & instead of and sometimes",
        "lol_lmao": "use lol or lmao once",
        "double_punctuation": "use !! or ?? once",
        "no_end_periods": "no periods at line ends",
        "word_merge": "merge two words once (gonnabe, tomorrowis)",
        "sparse_emoji": "one emoji somewhere (😭 🙄 ❤️)",
        "abbreviations": "use u, bc, idk, rn, ngl, tbh",
    }
    for q in quirks:
        if q in quirk_map:
            instructions.append(f"- {quirk_map[q]}")

    if instructions:
        return "STYLE:\n" + "\n".join(instructions)
    return ""


async def generate_note(llm_clients, persona: dict, relationship: dict,
                        topic: dict, mood: str, related_name: str,
                        has_title: bool, style: dict,
                        related_gender: str = "any") -> str:
    """Generate a note using Pass A (primary LLM)."""
    system_prompt, user_prompt = build_generation_prompt(
        persona, relationship, topic, mood, related_name,
        has_title, style["word_count"], style["line_count"],
        related_gender=related_gender,
    )

    note = await llm_clients.generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=style["temperature"],
        max_tokens=200,  # Short notes only
        presence_penalty=style.get("presence_penalty", 0.0),
        frequency_penalty=style.get("frequency_penalty", 0.0),
        provider="auto",
    )

    # Clean up any quotes or extra formatting
    note = note.strip().strip('"').strip("'")
    if note.startswith("```"):
        note = note.split("```")[1] if "```" in note[3:] else note[3:]
        note = note.strip()

    # Force line breaks if LLM returned a single-line block
    note = _force_line_breaks(note, has_title)

    # Truncate if too long
    lines = note.split('\n')
    max_lines = 6 if has_title else 4
    if len(lines) > max_lines:
        lines = lines[:max_lines]

    # Strip stubborn trailing periods randomly (except ellipsis) to keep some imperfection
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.endswith('.') and not stripped.endswith('..') and random.random() < 0.6:
            stripped = stripped[:-1]
            
        for char in [",", "/", "\\"]:
            if random.random() < 0.4:
                stripped = stripped.replace(char, " ")
                
        cleaned_lines.append(stripped)
    return "\n".join(cleaned_lines)


def _force_line_breaks(text: str, has_title: bool) -> str:
    """If the LLM returned everything on one line, split it into
    separate lines at natural thought boundaries."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # If we already have 3+ lines, it's fine
    if len(lines) >= 3:
        return '\n'.join(lines)

    # Single blob — split at thought boundaries
    blob = ' '.join(lines)
    words = blob.split()

    if len(words) <= 6:
        return blob  # Too short to split

    # Split at natural boundaries: after "i" followed by a verb-start,
    # or roughly every 5-10 words
    result_lines = []
    current = []
    target = random.randint(5, 10)

    for i, w in enumerate(words):
        current.append(w)
        at_boundary = False

        if len(current) >= target:
            at_boundary = True
        # Also break at natural points: before "i " starting a new thought
        elif len(current) >= 4 and i + 1 < len(words):
            next_w = words[i + 1]
            if next_w in ('i', 'he', 'she', 'we', 'they', 'its', 'the', 'my', 'his', 'her', 'need', 'maybe', 'gonna'):
                at_boundary = True

        if at_boundary:
            result_lines.append(' '.join(current))
            current = []
            target = random.randint(4, 9)

    if current:
        result_lines.append(' '.join(current))

    return '\n'.join(result_lines)


def sample_style() -> dict:
    """Sample style parameters for a note."""
    temp = random.choices(
        [0.85, 1.05, 1.20],
        weights=[25, 50, 25],
        k=1
    )[0]
    temp += random.uniform(-0.05, 0.05)

    # Word count: 10-30 (mode 18) — matches shorter 2-4 line notes
    word_count = int(random.triangular(10, 30, 18))

    # Line count: 2-4 lines as specifically requested
    line_count = random.randint(2, 4)

    presence_penalty = random.uniform(-0.1, 0.3)
    frequency_penalty = random.uniform(0.0, 0.4)

    return {
        "temperature": round(temp, 2),
        "word_count": word_count,
        "line_count": line_count,
        "presence_penalty": round(presence_penalty, 2),
        "frequency_penalty": round(frequency_penalty, 2),
    }
