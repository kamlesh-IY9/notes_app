"""Translator — Pass C: English → Hindi Devanagari via Google Translate (free, no API key)."""

import asyncio
import logging
import re
import time

log = logging.getLogger(__name__)

_SKIP_RE = re.compile(r'^[\d\s\+\-\(\)\.\@\/\:\#\_]+$')


def _has_devanagari(text: str) -> bool:
    return bool(re.search(r'[ऀ-ॿ]', text))


def _translate_sync(text: str) -> str:
    """Line-by-line Google Translate. Only numbers/email/symbols stay as-is."""
    from deep_translator import GoogleTranslator
    lines = text.split('\n')
    out = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            out.append(line)
            continue
        if _SKIP_RE.match(stripped):
            out.append(line)
            continue
        try:
            result = GoogleTranslator(source='en', target='hi').translate(stripped)
            if result and _has_devanagari(result):
                out.append(result)
            else:
                out.append(line)
            time.sleep(0.05)
        except Exception as e:
            log.warning("Google Translate failed for '%s': %s", stripped[:40], e)
            out.append(line)
    return '\n'.join(out)


async def translate_to_hindi(
    note_text: str,
    title: str | None,
    has_title: bool,
) -> tuple[str, str | None]:
    """Translate a note body (and optionally title) to Hindi Devanagari.

    Returns (translated_body, translated_title).
    Falls back to English text if translation fails.
    """
    loop = asyncio.get_event_loop()
    translated_note = await loop.run_in_executor(None, _translate_sync, note_text)

    if not _has_devanagari(translated_note):
        log.warning("Translation produced no Devanagari — keeping English")
        return note_text, title

    translated_title = title
    if has_title and title:
        translated_title = await loop.run_in_executor(None, _translate_sync, title)
        if not _has_devanagari(translated_title):
            translated_title = title

    return translated_note, translated_title
