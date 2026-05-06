"""Screenshot renderer — uses Playwright to render pixel-accurate phone screenshots.

Primary template: MIUI Notes (Xiaomi/Redmi) with 14 theme variants — matches the
user's reference samples. Secondary templates: Apple Notes, Google Keep, Samsung Notes.
"""

import asyncio
import html
import logging
import os
import random
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"

# Playwright browser singleton
_browser = None
_playwright = None


# Colorful MIUI theme variants (grey ones removed per user request)
MIUI_THEMES = [
    "yellow-italic",
    "warm-paper",
    "white-black",
    "boat-orange",
    "boat-white",
    "wallpaper-sunset",
    "wallpaper-gradient",
    "wallpaper-forest",
    "wallpaper-geometric",
    "wallpaper-bokeh",
    # Attractive themes batch 1
    "midnight-purple",
    "ocean-teal",
    "neon-coral",
    "lavender-pink",
    "mint-green",
    "amber-gold",
    # Attractive themes batch 2
    "rose-gold",
    "deep-navy",
    "cherry-blossom",
    "slate-emerald",
    "mocha-cream",
    "arctic-frost",
    "electric-indigo",
    "sunset-peach",
    # Attractive themes batch 3
    "forest-night",
    "cosmic-purple",
    "cherry-red",
    "cyber-mint",
    "dusk-rose",
    "arctic-cyan",
    "volcano-orange",
    "sapphire-deep",
    "champagne",
    "obsidian",
    # Batch 4 — rich dark tones
    "ruby-wine",
    "turquoise-depths",
    "lilac-night",
    "copper-bronze",
    "aurora-green",
    "terra-cotta",
    "midnight-indigo",
    "plum-haze",
    "ember-glow",
    "pine-shadow",
    # Batch 5 — moody naturals
    "seafoam-dark",
    "vintage-sepia",
    "ultraviolet",
    "steel-slate",
    "jade-deep",
    "sand-dusk",
    "crimson-night",
    "teal-forest",
    "neon-lime",
    "blush-noir",
    # Batch 6 — extra unique
    "burnt-umber",
    "glacier-blue",
    "orchid-dark",
    "honey-amber",
    "storm-grey",
    "blood-plum",
    "aquamarine-dark",
    "tobacco-brown",
    "electric-violet",
    "warm-charcoal",
    # Pattern themes — shapes, grids, textures
    "dot-matrix",
    "dot-matrix-blue",
    "diagonal-stripes",
    "grid-lines",
    "carbon-fiber",
    "starfield-deep",
    "bokeh-multicolor",
    "concentric-rings",
    "sunburst-amber",
    "marble-night",
    "woven-dark",
    "hex-glow",
    "crosshatch-navy",
    "geometric-triangles",
    "noise-purple",
]

# US carrier names — realistic mix for status bar (English jobs)
US_CARRIERS = [
    "T-Mobile", "AT&T", "Verizon", "T-Mobile", "AT&T", "Verizon",
    "T-Mobile", "AT&T",  # weighted heavier (big 3)
    "US Cellular", "Mint", "Cricket", "Metro",
    "Visible", "Google Fi", "Straight Talk", "Boost",
]

# Indian carrier names — for Hindi jobs
INDIA_CARRIERS = [
    "Jio", "Jio", "Jio",          # Jio is most common
    "Airtel", "Airtel", "Airtel",  # Airtel second most common
    "Vi", "Vi",                    # Vodafone Idea
    "BSNL",
]

# Font families per phone type — realistic system fonts
FONT_FAMILIES = {
    "apple_notes": [
        "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
        "'Inter', 'Helvetica Neue', sans-serif",
        "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    ],
    "samsung_notes": [
        "'Roboto', 'Samsung Sans', sans-serif",
        "'Roboto', sans-serif",
        "'Noto Sans', 'Roboto', sans-serif",
    ],
    "google_keep": [
        "'Roboto', 'Google Sans', sans-serif",
        "'Google Sans', 'Roboto', sans-serif",
        "'Noto Sans', 'Roboto', sans-serif",
    ],
}

# Devanagari font stack — used for Hindi jobs across all app types
FONT_FAMILIES_HINDI = {
    "apple_notes": [
        "'Noto Sans Devanagari', 'Inter', sans-serif",
        "'Noto Sans Devanagari', -apple-system, sans-serif",
    ],
    "samsung_notes": [
        "'Noto Sans Devanagari', 'Roboto', sans-serif",
        "'Noto Sans Devanagari', 'Noto Sans', sans-serif",
    ],
    "google_keep": [
        "'Noto Sans Devanagari', 'Roboto', sans-serif",
        "'Noto Sans Devanagari', 'Google Sans', sans-serif",
    ],
    "miui_notes": [
        "'Noto Sans Devanagari', 'Roboto', sans-serif",
        "'Noto Sans Devanagari', sans-serif",
    ],
}

# Wallpaper CSS — gradient-based so we don't need image files
WALLPAPER_CSS = {
    "boat-orange": "linear-gradient(180deg, #0a1828 0%, #1a3a5a 60%, #2a4a6a 100%)",
    "boat-white": "linear-gradient(180deg, #0a1828 0%, #1a3a5a 60%, #2a4a6a 100%)",
    "wallpaper-sunset": "linear-gradient(180deg, #1a1d3a 0%, #6e3e63 40%, #d97a4a 70%, #f0c97a 100%)",
    "wallpaper-gradient": "linear-gradient(135deg, #ee7752 0%, #e73c7e 30%, #23a6d5 70%, #23d5ab 100%)",
    "wallpaper-forest": "linear-gradient(180deg, #0c2818 0%, #1a4028 40%, #2a5840 80%, #3a7050 100%)",
    "wallpaper-geometric": "radial-gradient(circle at 30% 20%, #ff6b9d 0%, transparent 40%), radial-gradient(circle at 70% 80%, #5dadec 0%, transparent 50%), linear-gradient(135deg, #2c1a4d 0%, #4a2870 100%)",
    "wallpaper-bokeh": "radial-gradient(circle at 20% 30%, rgba(255,200,100,0.6) 0%, transparent 8%), radial-gradient(circle at 70% 60%, rgba(100,200,255,0.5) 0%, transparent 10%), radial-gradient(circle at 40% 80%, rgba(255,150,200,0.5) 0%, transparent 8%), linear-gradient(180deg, #1a1a2e 0%, #16213e 100%)",
    # Attractive themes batch 3 (gradient versions for visual richness)
    "forest-night": "linear-gradient(180deg, #061410 0%, #0e2820 50%, #1a3a30 100%)",
    "cosmic-purple": "radial-gradient(circle at 30% 20%, #6a2ea8 0%, transparent 60%), linear-gradient(135deg, #0a0518 0%, #1a0a30 100%)",
    "cherry-red": "linear-gradient(180deg, #1a0608 0%, #2a0a10 50%, #3a1018 100%)",
    "cyber-mint": "linear-gradient(135deg, #001a14 0%, #002a20 50%, #003830 100%)",
    "dusk-rose": "linear-gradient(180deg, #2a0e1a 0%, #3a1428 60%, #4a1a35 100%)",
    "arctic-cyan": "linear-gradient(180deg, #00161e 0%, #002030 50%, #003040 100%)",
    "volcano-orange": "linear-gradient(180deg, #1a0805 0%, #2e1208 50%, #441a08 100%)",
    "sapphire-deep": "linear-gradient(180deg, #050a1e 0%, #0a142e 50%, #0e1c40 100%)",
    "champagne": "linear-gradient(180deg, #1a1408 0%, #2a2010 50%, #382c18 100%)",
    "obsidian": "linear-gradient(180deg, #0a0a0a 0%, #141418 50%, #1c1c20 100%)",
    # Batch 4
    "ruby-wine": "linear-gradient(180deg, #1a0510 0%, #2e0a1c 50%, #420e28 100%)",
    "turquoise-depths": "linear-gradient(180deg, #001e1e 0%, #002e2a 50%, #003c36 100%)",
    "lilac-night": "linear-gradient(135deg, #100a20 0%, #1e1035 50%, #2c1848 100%)",
    "copper-bronze": "linear-gradient(180deg, #1a0e00 0%, #2c1a06 50%, #3e260a 100%)",
    "aurora-green": "radial-gradient(ellipse at 50% 0%, #00b894 0%, transparent 60%), linear-gradient(180deg, #020c14 0%, #041824 100%)",
    "terra-cotta": "linear-gradient(180deg, #1e0e08 0%, #2e1610 50%, #401e18 100%)",
    "midnight-indigo": "linear-gradient(180deg, #04040e 0%, #080818 50%, #0e0e28 100%)",
    "plum-haze": "radial-gradient(circle at 60% 40%, #6b2d8c 0%, transparent 50%), linear-gradient(180deg, #0e0416 0%, #1a0828 100%)",
    "ember-glow": "radial-gradient(ellipse at 50% 80%, #ff5900 0%, transparent 50%), linear-gradient(180deg, #0e0600 0%, #1e0e00 100%)",
    "pine-shadow": "linear-gradient(180deg, #040e08 0%, #081c10 50%, #0e2818 100%)",
    # Batch 5
    "seafoam-dark": "linear-gradient(135deg, #001e18 0%, #003028 50%, #004038 100%)",
    "vintage-sepia": "linear-gradient(180deg, #14100a 0%, #221a0e 50%, #302414 100%)",
    "ultraviolet": "radial-gradient(circle at 40% 30%, #5500cc 0%, transparent 55%), linear-gradient(135deg, #04000e 0%, #0c0020 100%)",
    "steel-slate": "linear-gradient(180deg, #0c1018 0%, #141c26 50%, #1c2634 100%)",
    "jade-deep": "linear-gradient(180deg, #001a0e 0%, #002c18 50%, #003c22 100%)",
    "sand-dusk": "linear-gradient(180deg, #1a1208 0%, #2c1e0e 50%, #3c2c16 100%)",
    "crimson-night": "linear-gradient(180deg, #140008 0%, #20000e 50%, #300016 100%)",
    "teal-forest": "linear-gradient(135deg, #001818 0%, #002828 50%, #003838 100%)",
    "neon-lime": "radial-gradient(ellipse at 50% 80%, #39ff14 0%, transparent 55%), linear-gradient(180deg, #020800 0%, #061200 100%)",
    "blush-noir": "linear-gradient(135deg, #14080e 0%, #200e18 50%, #2e1422 100%)",
    # Batch 6
    "burnt-umber": "linear-gradient(180deg, #140800 0%, #221200 50%, #301c04 100%)",
    "glacier-blue": "linear-gradient(180deg, #00101e 0%, #001c30 50%, #002840 100%)",
    "orchid-dark": "linear-gradient(135deg, #140420 0%, #200830 50%, #2e1040 100%)",
    "honey-amber": "linear-gradient(180deg, #1a0e00 0%, #2c1800 50%, #3e2400 100%)",
    "storm-grey": "linear-gradient(180deg, #0a0c10 0%, #121418 50%, #1a1c22 100%)",
    "blood-plum": "linear-gradient(180deg, #180010 0%, #26001c 50%, #360028 100%)",
    "aquamarine-dark": "linear-gradient(135deg, #001a14 0%, #002c22 50%, #003c30 100%)",
    "tobacco-brown": "linear-gradient(180deg, #180e00 0%, #261600 50%, #342000 100%)",
    "electric-violet": "radial-gradient(circle at 50% 20%, #7c00ff 0%, transparent 50%), linear-gradient(180deg, #06000e 0%, #100018 100%)",
    "warm-charcoal": "linear-gradient(180deg, #141210 0%, #201e1c 50%, #2c2a28 100%)",
    # Pattern themes — shapes, grids, textures (CSS patterns via background shorthand)
    "dot-matrix": (
        "radial-gradient(circle, rgba(255,255,255,0.14) 1.5px, transparent 1.5px) 0 0 / 22px 22px, "
        "linear-gradient(180deg, #080810 0%, #101018 100%)"
    ),
    "dot-matrix-blue": (
        "radial-gradient(circle, rgba(80,160,255,0.22) 1.5px, transparent 1.5px) 0 0 / 18px 18px, "
        "linear-gradient(180deg, #02051a 0%, #060a24 100%)"
    ),
    "diagonal-stripes": (
        "repeating-linear-gradient(45deg, transparent 0px, transparent 14px, "
        "rgba(255,255,255,0.05) 14px, rgba(255,255,255,0.05) 15px), "
        "linear-gradient(180deg, #080810 0%, #14141e 100%)"
    ),
    "grid-lines": (
        "repeating-linear-gradient(0deg, rgba(255,255,255,0.055) 0, rgba(255,255,255,0.055) 1px, "
        "transparent 1px, transparent 26px), "
        "repeating-linear-gradient(90deg, rgba(255,255,255,0.055) 0, rgba(255,255,255,0.055) 1px, "
        "transparent 1px, transparent 26px), "
        "linear-gradient(180deg, #050508 0%, #0c0c12 100%)"
    ),
    "carbon-fiber": (
        "repeating-linear-gradient(45deg, rgba(255,255,255,0.04) 0px, rgba(255,255,255,0.04) 3px, "
        "transparent 3px, transparent 7px), "
        "repeating-linear-gradient(-45deg, rgba(255,255,255,0.04) 0px, rgba(255,255,255,0.04) 3px, "
        "transparent 3px, transparent 7px), "
        "linear-gradient(180deg, #060606 0%, #101010 100%)"
    ),
    "starfield-deep": (
        "radial-gradient(circle, rgba(255,255,255,0.85) 1px, transparent 1px) 0 0 / 42px 42px, "
        "radial-gradient(circle, rgba(255,255,255,0.5) 1px, transparent 1px) 21px 21px / 64px 64px, "
        "radial-gradient(circle, rgba(255,255,255,0.3) 0.5px, transparent 0.5px) 8px 8px / 28px 28px, "
        "linear-gradient(180deg, #01010a 0%, #04041a 100%)"
    ),
    "bokeh-multicolor": (
        "radial-gradient(circle at 15% 25%, rgba(255,80,140,0.28) 0%, transparent 18%), "
        "radial-gradient(circle at 80% 15%, rgba(80,140,255,0.22) 0%, transparent 14%), "
        "radial-gradient(circle at 55% 70%, rgba(120,255,160,0.18) 0%, transparent 20%), "
        "radial-gradient(circle at 22% 78%, rgba(255,200,80,0.22) 0%, transparent 12%), "
        "radial-gradient(circle at 88% 65%, rgba(200,80,255,0.20) 0%, transparent 16%), "
        "radial-gradient(circle at 45% 40%, rgba(80,220,255,0.15) 0%, transparent 22%), "
        "linear-gradient(180deg, #040406 0%, #0a0a0e 100%)"
    ),
    "concentric-rings": (
        "radial-gradient(circle at 50% 58%, transparent 15%, rgba(255,255,255,0.045) 15%, rgba(255,255,255,0.045) 16.5%, transparent 16.5%), "
        "radial-gradient(circle at 50% 58%, transparent 30%, rgba(255,255,255,0.04) 30%, rgba(255,255,255,0.04) 31.5%, transparent 31.5%), "
        "radial-gradient(circle at 50% 58%, transparent 48%, rgba(255,255,255,0.035) 48%, rgba(255,255,255,0.035) 49.5%, transparent 49.5%), "
        "radial-gradient(circle at 50% 58%, transparent 68%, rgba(255,255,255,0.025) 68%, rgba(255,255,255,0.025) 69.5%, transparent 69.5%), "
        "linear-gradient(180deg, #04040e 0%, #0a0a1c 100%)"
    ),
    "sunburst-amber": (
        "repeating-conic-gradient(from 0deg at 50% 68%, rgba(255,190,60,0.07) 0deg, "
        "rgba(255,190,60,0.07) 5deg, transparent 5deg, transparent 10deg), "
        "linear-gradient(180deg, #0a0700 0%, #180f00 100%)"
    ),
    "marble-night": (
        "radial-gradient(ellipse at 20% 50%, rgba(180,180,230,0.13) 0%, transparent 45%), "
        "radial-gradient(ellipse at 80% 20%, rgba(140,130,210,0.10) 0%, transparent 38%), "
        "radial-gradient(ellipse at 60% 85%, rgba(100,100,190,0.09) 0%, transparent 35%), "
        "repeating-linear-gradient(54deg, transparent 0px, transparent 9px, "
        "rgba(255,255,255,0.025) 9px, rgba(255,255,255,0.025) 10px), "
        "linear-gradient(180deg, #06060e 0%, #0e0e1c 100%)"
    ),
    "woven-dark": (
        "repeating-linear-gradient(0deg, rgba(255,255,255,0.045) 0px, rgba(255,255,255,0.045) 2px, "
        "transparent 2px, transparent 12px), "
        "repeating-linear-gradient(90deg, rgba(255,255,255,0.045) 0px, rgba(255,255,255,0.045) 2px, "
        "transparent 2px, transparent 12px), "
        "linear-gradient(180deg, #060606 0%, #121212 100%)"
    ),
    "hex-glow": (
        "radial-gradient(circle at 30% 25%, rgba(0,210,255,0.14) 0%, transparent 32%), "
        "radial-gradient(circle at 70% 75%, rgba(0,255,160,0.12) 0%, transparent 32%), "
        "repeating-linear-gradient(60deg, rgba(255,255,255,0.03) 0px, rgba(255,255,255,0.03) 1px, "
        "transparent 1px, transparent 22px), "
        "repeating-linear-gradient(-60deg, rgba(255,255,255,0.03) 0px, rgba(255,255,255,0.03) 1px, "
        "transparent 1px, transparent 22px), "
        "repeating-linear-gradient(0deg, rgba(255,255,255,0.02) 0px, rgba(255,255,255,0.02) 1px, "
        "transparent 1px, transparent 22px), "
        "linear-gradient(180deg, #020c10 0%, #061420 100%)"
    ),
    "crosshatch-navy": (
        "repeating-linear-gradient(45deg, rgba(80,130,255,0.07) 0px, rgba(80,130,255,0.07) 1px, "
        "transparent 1px, transparent 16px), "
        "repeating-linear-gradient(-45deg, rgba(80,130,255,0.07) 0px, rgba(80,130,255,0.07) 1px, "
        "transparent 1px, transparent 16px), "
        "linear-gradient(180deg, #030818 0%, #070d24 100%)"
    ),
    "geometric-triangles": (
        "repeating-linear-gradient(60deg, transparent 0px, transparent 20px, "
        "rgba(255,255,255,0.04) 20px, rgba(255,255,255,0.04) 21px), "
        "repeating-linear-gradient(-60deg, transparent 0px, transparent 20px, "
        "rgba(255,255,255,0.04) 20px, rgba(255,255,255,0.04) 21px), "
        "repeating-linear-gradient(0deg, transparent 0px, transparent 20px, "
        "rgba(255,255,255,0.04) 20px, rgba(255,255,255,0.04) 21px), "
        "linear-gradient(180deg, #08080a 0%, #141416 100%)"
    ),
    "noise-purple": (
        "radial-gradient(circle at 22% 40%, rgba(130,60,210,0.32) 0%, transparent 38%), "
        "radial-gradient(circle at 76% 30%, rgba(90,40,170,0.26) 0%, transparent 32%), "
        "radial-gradient(circle at 50% 82%, rgba(170,80,255,0.22) 0%, transparent 42%), "
        "repeating-linear-gradient(30deg, rgba(255,255,255,0.018) 0px, rgba(255,255,255,0.018) 1px, "
        "transparent 1px, transparent 16px), "
        "linear-gradient(180deg, #060310 0%, #10061e 100%)"
    ),
}


async def get_browser():
    """Get or create the Playwright browser instance."""
    global _browser, _playwright
    if _browser is None:
        from playwright.async_api import async_playwright
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(headless=True)
        log.info("Playwright browser launched")
    return _browser


async def close_browser():
    """Close the Playwright browser."""
    global _browser, _playwright
    if _browser:
        try:
            await _browser.close()
        except Exception as e:
            log.debug("Browser close ignored during shutdown: %s", e)
        _browser = None
    if _playwright:
        try:
            await _playwright.stop()
        except Exception:
            pass
        _playwright = None


async def render_screenshot(
    note_text: str,
    has_title: bool,
    app_type: str,
    theme: str,
    note_date: datetime,
    connectivity: str,
    output_path: str,
    language: str = "english",
) -> str:
    """Render a phone screenshot and save as JPEG.

    Returns the output path.

    For MIUI Notes (the primary template), `theme` is one of MIUI_THEMES.
    For other apps, `theme` is "light" or "dark".
    """
    browser = await get_browser()

    # Load template
    template_map = {
        "miui_notes": "miui_notes.html",
        "apple_notes": "apple_notes.html",
        "google_keep": "google_keep.html",
        "samsung_notes": "samsung_notes.html",
    }
    template_file = TEMPLATES_DIR / template_map.get(app_type, "miui_notes.html")
    template_html = template_file.read_text()

    # Build template variables
    if app_type == "miui_notes":
        replacements = _build_miui_vars(note_text, has_title, theme, note_date, language=language)
        size = {"width": 1170, "height": 2532}
    else:
        replacements = _build_legacy_vars(
            note_text, has_title, app_type, theme, note_date, connectivity, language=language
        )
        sizes = {
            "apple_notes": {"width": 1170, "height": 2532},   # iPhone 14/15
            "google_keep": {"width": 1080, "height": 2400},   # Pixel 7
            "samsung_notes": {"width": 1080, "height": 2340}, # Galaxy S23
        }
        size = sizes.get(app_type, {"width": 1170, "height": 2532})

    # Apply replacements
    for key, value in replacements.items():
        template_html = template_html.replace(f"{{{{{key}}}}}", str(value))

    # Render with Playwright
    page = await browser.new_page(viewport=size)
    await page.set_content(template_html, wait_until="networkidle")

    # Wait for fonts to load
    await asyncio.sleep(0.5)

    # Random JPEG quality (82-95)
    quality = random.randint(82, 95)

    # Save as JPEG
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    await page.screenshot(
        path=output_path,
        type="jpeg",
        quality=quality,
        full_page=False,
    )

    await page.close()
    log.info("Screenshot saved: %s (%s/%s, q=%d)", output_path, app_type, theme, quality)
    return output_path


# ────────────────────────────────────────────────────────────────────────────
# MIUI Notes template builder (the primary look)
# ────────────────────────────────────────────────────────────────────────────

def _build_miui_vars(
    note_text: str,
    has_title: bool,
    theme: str,
    note_date: datetime,
    language: str = "english",
) -> dict:
    """Build template variables for the MIUI Notes template."""
    if theme not in MIUI_THEMES:
        theme = "midnight-purple"

    vars = {"THEME": theme}

    # Font family — Devanagari stack for Hindi, Roboto otherwise
    if language == "hindi":
        font_pool = FONT_FAMILIES_HINDI["miui_notes"]
    else:
        font_pool = ["'Roboto', 'Helvetica Neue', sans-serif", "'Roboto', sans-serif"]
    vars["FONT_FAMILY"] = random.choice(font_pool)

    # Wallpaper layer (only for wallpaper themes + boat themes)
    if theme in WALLPAPER_CSS:
        vars["WALLPAPER_DIV"] = (
            f'<div class="wallpaper" style="background: {WALLPAPER_CSS[theme]};"></div>'
        )
    else:
        vars["WALLPAPER_DIV"] = ""

    # ── Status bar clock (24-hour HH:MM, jittered ±5 min from note date) ──
    jitter_min = random.randint(-5, 5)
    h = note_date.hour
    m = (note_date.minute + jitter_min) % 60
    if note_date.minute + jitter_min < 0:
        h = (h - 1) % 24
    elif note_date.minute + jitter_min >= 60:
        h = (h + 1) % 24
    vars["STATUS_TIME"] = f"{h}:{m:02d}"

    # ── Notification icons in status bar (0–4 random app icons) ──
    vars["NOTIF_ICONS"] = _build_notif_icons()

    # ── VoNR stack (Vo / NR vertical text) ──
    vars["VONR_STACK"] = '<div class="vonr-stack">Vo<br>NR</div>'

    # ── Data rate stack (X.XX KB/s) ──
    rate = round(random.uniform(0.5, 15.0), 2)
    vars["DATA_STACK"] = f'<div class="data-stack">{rate}<br>KB/s</div>'

    # ── 5G+ stack with up/down arrows ──
    label = random.choice(["5G+", "5G", "LTE", "4G+"])
    vars["GNET_STACK"] = f'<div class="gnet-stack"><div class="label">{label}</div><div class="arrows">↕</div></div>'

    # ── Signal bars HTML ──
    num_bars = random.randint(2, 4)
    bars = []
    for i in range(4):
        cls = "bar" if i < num_bars else "bar empty"
        bars.append(f'<div class="{cls}"></div>')
    vars["SIGNAL_BARS"] = "".join(bars)

    # ── Battery ──
    batt_pct = random.randint(15, 99)
    if batt_pct < 20:
        vars["BATT_FILL_CLASS"] = "battery-fill low"
    elif random.random() < 0.20:
        vars["BATT_FILL_CLASS"] = "battery-fill charging"
    else:
        vars["BATT_FILL_CLASS"] = "battery-fill"
    vars["BATT_PCT"] = batt_pct

    # ── Notification banner (Disabled per user request) ──
    vars["NOTIF_BANNER_VISIBLE"] = ""
    vars["NOTIF_NAME"] = ""
    vars["NOTIF_AVATAR_LETTER"] = ""
    vars["NOTIF_PREVIEW"] = ""
    vars["NOTIF_WHEN"] = ""

    # ── Title placeholder vs real title ──
    lines = [l for l in note_text.split("\n") if l.strip()]
    if has_title and lines:
        title_text = lines[0].strip()
        body_lines = lines[1:]
        vars["TITLE_TEXT"] = html.escape(title_text)
        vars["TITLE_CLASS"] = "has-title"
    else:
        # Empty Title placeholder (matches all reference samples)
        vars["TITLE_TEXT"] = "Title"
        vars["TITLE_CLASS"] = ""
        body_lines = lines

    # ── Date label "M/D/YYYY, HH:MM" ──
    vars["DATE_LABEL"] = (
        f"{note_date.month}/{note_date.day}/{note_date.year}, "
        f"{note_date.hour}:{note_date.minute:02d}"
    )

    # ── Char count (count body chars, not including title) ──
    body_text = "\n".join(body_lines).strip()
    vars["CHAR_COUNT"] = len(body_text)

    # ── Body text with HTML escape, preserving line breaks ──
    vars["BODY_TEXT"] = html.escape(body_text)

    # ── Per-render letter-spacing jitter ──
    vars["LETTER_SPACING"] = round(random.uniform(-0.3, 0.3), 2)

    return vars


def _build_notif_icons() -> str:
    """Build 0–4 notification app icons in the status bar."""
    icon_classes = [
        "icon-snap", "icon-insta", "icon-telegram",
        "icon-whatsapp", "icon-gmail", "icon-fb",
    ]
    n = random.randint(0, 4)
    if n == 0:
        return ""
    chosen = random.sample(icon_classes, k=min(n, len(icon_classes)))
    return "".join(f'<span class="icon {c}"></span>' for c in chosen)


# ────────────────────────────────────────────────────────────────────────────
# Legacy template builders (Apple Notes / Google Keep / Samsung Notes)
# ────────────────────────────────────────────────────────────────────────────

# Folder/breadcrumb labels — varied per render to avoid the dead-giveaway hardcoded text.
# Mirrors what real users actually have as note-folder names.
FOLDER_LABELS = [
    "Notes", "All iCloud", "iCloud", "Personal", "Family",
    "Quick Notes", "Random", "Stuff", "Important", "Daily",
    "Diary", "Thoughts", "Journal", "Misc", "Reminders",
    "On My iPhone", "Recent", "All Notes", "Drafts", "To Read",
]


def _build_legacy_vars(
    note_text: str,
    has_title: bool,
    app_type: str,
    theme: str,
    note_date: datetime,
    connectivity: str,
    language: str = "english",
) -> dict:
    """Build template variables for the legacy (non-MIUI) templates."""
    vars = {"THEME": theme}
    vars["FOLDER_LABEL"] = random.choice(FOLDER_LABELS)

    # Font family — use Devanagari stack for Hindi, otherwise normal system fonts
    if language == "hindi":
        font_pool = FONT_FAMILIES_HINDI.get(app_type, FONT_FAMILIES_HINDI["google_keep"])
    else:
        font_pool = FONT_FAMILIES.get(app_type, FONT_FAMILIES["google_keep"])
    vars["FONT_FAMILY"] = random.choice(font_pool)

    months_full = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    months_short = [
        "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]

    hour12 = note_date.hour % 12 or 12
    ampm = "AM" if note_date.hour < 12 else "PM"
    time12 = f"{hour12}:{note_date.minute:02d} {ampm}"

    if app_type == "apple_notes":
        date_str = f"{months_full[note_date.month]} {note_date.day}, {note_date.year} at {time12}"
    elif app_type == "google_keep":
        date_str = f"Edited {months_short[note_date.month]} {note_date.day}, {note_date.year}, {time12}"
    else:
        date_str = f"{months_short[note_date.month]} {note_date.day}, {note_date.year}, {time12}"

    vars["DATE_LABEL"] = date_str

    # Status bar time (12h for Apple, can be 12h or 24h for Android)
    sh12 = note_date.hour % 12 or 12
    jitter_min = random.randint(-5, 5)
    sm = max(0, min(59, note_date.minute + jitter_min))
    if app_type == "apple_notes":
        vars["STATUS_TIME"] = f"{sh12}:{sm:02d}"
    else:
        # Android: ~30% chance of 24h format
        if random.random() < 0.30:
            h24 = note_date.hour
            vars["STATUS_TIME"] = f"{h24}:{sm:02d}"
        else:
            vars["STATUS_TIME"] = f"{sh12}:{sm:02d}"

    # Connectivity and status bar elements
    vars.update(_build_connectivity_vars(connectivity, theme, app_type, language))

    # Note content
    vars["NOTE_CONTENT"] = _build_note_html(note_text, has_title)

    # Per-render jitter
    vars["BODY_OFFSET"] = random.randint(0, 8) if random.random() < 0.1 else 0
    vars["LETTER_SPACING"] = round(random.uniform(-0.1, 0.1), 2)
    vars["TITLE_SIZE"] = {"apple_notes": 56, "google_keep": 58, "samsung_notes": 54}.get(app_type, 56)
    vars["BODY_SIZE"] = {"apple_notes": 46, "google_keep": 48, "samsung_notes": 46}.get(app_type, 46)

    return vars


def _build_connectivity_vars(connectivity: str, theme: str, app_type: str = "", language: str = "english") -> dict:
    vars = {}

    # ── Signal bars (scaled heights for high-DPI viewport) ──
    if connectivity in ("wifi_cellular", "cellular_only"):
        num_bars = random.randint(1, 4)
        bars_html = '<div class="signal-bars">'
        for i in range(4):
            heights = [8, 14, 20, 28]  # scaled for 1080-1170px viewport
            bar_class = "" if i < num_bars else " empty"
            bars_html += f'<div class="bar{bar_class}" style="height:{heights[i]}px"></div>'
        bars_html += '</div>'
        vars["SIGNAL_BARS"] = bars_html
    else:
        vars["SIGNAL_BARS"] = ""

    # ── WiFi icon ──
    if connectivity in ("wifi_cellular", "wifi_only"):
        vars["WIFI_ICON"] = '<svg class="wifi-icon" viewBox="0 0 24 24"><path d="M1 9l2 2c4.97-4.97 13.03-4.97 18 0l2-2C16.93 2.93 7.08 2.93 1 9zm8 8l3 3 3-3c-1.65-1.66-4.34-1.66-6 0zm-4-4l2 2c2.76-2.76 7.24-2.76 10 0l2-2C15.14 9.14 8.87 9.14 5 13z"/></svg>'
    else:
        vars["WIFI_ICON"] = ""

    # ── Carrier name (Android only, iPhone hides carrier on modern models) ──
    if app_type in ("samsung_notes", "google_keep"):
        # 55% chance to show carrier name on Android
        if random.random() < 0.55:
            carrier_pool = INDIA_CARRIERS if language == "hindi" else US_CARRIERS
            vars["CARRIER_NAME"] = random.choice(carrier_pool)
        else:
            vars["CARRIER_NAME"] = ""
    else:
        vars["CARRIER_NAME"] = ""  # iPhone doesn't show carrier post-X

    # ── Network badge (5G/LTE/4G) ──
    if connectivity in ("wifi_cellular", "cellular_only"):
        # Show badge more often — 60% chance
        if random.random() < 0.60:
            badge = random.choice(["5G", "5G", "LTE", "LTE", "4G"])
            vars["BADGE"] = f'<span class="badge-5g">{badge}</span>'
        else:
            vars["BADGE"] = ""
    elif connectivity == "no_service":
        vars["BADGE"] = '<span class="no-service">No Service</span>'
    else:
        vars["BADGE"] = ""

    if connectivity == "no_service":
        vars["SIGNAL_BARS"] = ""

    # ── Battery (with percentage text) ──
    battery_pct = random.randint(5, 100)
    is_charging = random.random() < 0.20
    fill_class = "battery-fill"
    if battery_pct < 20:
        fill_class += " low"
    elif is_charging:
        fill_class += " charging"

    # Show battery percentage text ~65% of the time (common on real phones)
    show_pct = random.random() < 0.65
    pct_text = f'<span class="battery-pct">{battery_pct}%</span>' if show_pct else ""
    charge_icon = "⚡" if is_charging and random.random() < 0.5 else ""

    battery_html = (
        f'<div class="battery" style="display:flex;align-items:center;gap:4px">'
        f'{charge_icon}'
        f'<div class="battery-body"><div class="{fill_class}" style="width:{battery_pct}%"></div></div>'
        f'<div class="battery-tip"></div>'
        f'{pct_text}'
        f'</div>'
    )
    vars["BATTERY"] = battery_html
    return vars



def _build_note_html(note_text: str, has_title: bool) -> str:
    lines = note_text.split('\n')
    lines = [l for l in lines if l.strip() or l == ""]
    if not lines:
        return '<div class="note-body">Empty note</div>'
    if has_title and len(lines) >= 2:
        title = html.escape(lines[0])
        body_lines = lines[1:]
        body = html.escape('\n'.join(body_lines))
        return f'<div class="note-title">{title}</div>\n<div class="note-body">{body}</div>'
    if lines:
        first = html.escape(lines[0])
        rest = html.escape('\n'.join(lines[1:])) if len(lines) > 1 else ""
        return f'<div class="note-body no-title"><span class="first-line">{first}</span>\n{rest}</div>'
    return '<div class="note-body">Empty note</div>'
