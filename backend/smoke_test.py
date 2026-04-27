"""Standalone smoke test — generates 3 MIUI screenshots without the API, to verify rendering."""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Load env
from dotenv import load_dotenv
backend_dir = Path(__file__).parent
load_dotenv(backend_dir.parent / ".env")

# Make backend imports work
sys.path.insert(0, str(backend_dir.parent))

from backend.core.screenshot import render_screenshot, close_browser, MIUI_THEMES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# Hard-coded sample notes — bypass LLM entirely so we can isolate the rendering
SAMPLES = [
    # (note_text, has_title, theme_index)
    (
        "harvey my piano teacher and his cousin miles were tuning keys together\n"
        "both kept correcting each other while playing same note\n"
        "sound kept changing every second\n"
        "ended up stepping away\n"
        "ears started hurting from that back and forth",
        False, 5,  # warm-paper (matches Piano sample)
    ),
    (
        "marley my coworker told august his manager something i said\n"
        "but it sounded slightly changed\n"
        "august reacted stronger didnt correct it\n"
        "just let it pass",
        False, 1,  # black-white (matches sample 2)
    ),
    (
        "clark my boss and his client simon reviewed plans\n"
        "papers spread across table lines and marks everywhere\n"
        "discussion paused midway as both rechecked numbers",
        False, 3,  # black-blue (matches sample 4)
    ),
    (
        "derek the one who handles repairs for our place brought his frined sam who works on cars\n"
        "derek told him i understand mechanical stuff\n"
        "sam started explaining everything like i follow it",
        False, 2,  # yellow-italic (matches sample 3)
    ),
    (
        "garrett cousin from dad side told milo roomate he stays with that i might join their plan\n"
        "never said that cearly\n"
        "milo alredy looking at dates",
        False, 0,  # gray-white (matches sample 1)
    ),
    (
        "peter, a senior at office, told julian his client that douments were prepared by me they were incomplete\n"
        "julian started reviewing them",
        False, 7,  # boat-orange
    ),
    (
        "Piano\n"
        "harvey my piano teacher and his cousin miles were tuning keys together\n"
        "both kept correcting each other while playing same note\n"
        "sound kept changing every second\n"
        "ended up stepping away",
        True, 5,  # warm-paper, has-title
    ),
    (
        "mark my coach and his assistant dean watched practice clips\n"
        "they paused same moment multiple times\n"
        "each pointing at something else screen kept replaying\n"
        "no final comment came",
        False, 4,  # gray-blue (matches sample 4)
    ),
    (
        "called grandma yesterday she sounded tired\n"
        "told me about uncle ray fixing the porch\n"
        "asked if i was eating ok\n"
        "miss her cooking already",
        False, 9,  # wallpaper-sunset
    ),
    (
        "wilson my best friend texted me about his sister beth\n"
        "she got the job at the hospital finally\n"
        "wilson sounded so proud over the phone\n"
        "told him to bring her over saturday",
        False, 11,  # wallpaper-forest
    ),
]


async def main():
    """Render 10 sample MIUI screenshots, one per theme."""
    out_dir = backend_dir.parent / "output" / "smoke"
    out_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now()

    for idx, (note_text, has_title, theme_idx) in enumerate(SAMPLES):
        theme = MIUI_THEMES[theme_idx % len(MIUI_THEMES)]
        out_path = out_dir / f"smoke_{idx + 1:02d}_{theme}.jpg"

        # Vary the time
        note_date = today.replace(
            hour=(idx * 3 + 12) % 24,
            minute=(idx * 7 + 19) % 60,
        )

        log.info("Rendering %d/10: theme=%s → %s", idx + 1, theme, out_path.name)
        await render_screenshot(
            note_text=note_text,
            has_title=has_title,
            app_type="miui_notes",
            theme=theme,
            note_date=note_date,
            connectivity="wifi_cellular",
            output_path=str(out_path),
        )

    await close_browser()
    log.info("Smoke test complete: %d screenshots in %s", len(SAMPLES), out_dir)


if __name__ == "__main__":
    asyncio.run(main())
