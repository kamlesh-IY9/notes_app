"""Quick render of the 10 new MIUI themes to verify they don't crash."""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

backend_dir = Path(__file__).parent
load_dotenv(backend_dir.parent / ".env")
sys.path.insert(0, str(backend_dir.parent))

from backend.core.screenshot import render_screenshot, close_browser

logging.basicConfig(level=logging.INFO, format="%(message)s")

NEW_THEMES = [
    "forest-night", "cosmic-purple", "cherry-red", "cyber-mint",
    "dusk-rose", "arctic-cyan", "volcano-orange", "sapphire-deep",
    "champagne", "obsidian",
]

NOTE = (
    "my friend alex called about the dog walk schedule\n"
    "we usually meet at the park around 7\n"
    "told her i can swap monday for tuesday\n"
    "kids cant make it that day"
)


async def main():
    out = backend_dir.parent / "output" / "smoke_new_themes"
    out.mkdir(parents=True, exist_ok=True)
    today = datetime.now()

    for i, theme in enumerate(NEW_THEMES):
        path = out / f"{i + 1:02d}_{theme}.jpg"
        await render_screenshot(
            note_text=NOTE,
            has_title=False,
            app_type="miui_notes",
            theme=theme,
            note_date=today.replace(hour=(i * 2 + 9) % 24, minute=(i * 11) % 60),
            connectivity="wifi_cellular",
            output_path=str(path),
        )
        print(f"  ✓ {theme}")

    await close_browser()
    print(f"\nAll 10 new themes rendered to {out}")


if __name__ == "__main__":
    asyncio.run(main())
