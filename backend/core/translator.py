"""Translator — Pass C: English → target language via Google Translate (free, no API key)."""

import asyncio
import logging
import re
import time

log = logging.getLogger(__name__)

_SKIP_RE = re.compile(r'^[\d\s\+\-\(\)\.\@\/\:\#\_]+$')


def _has_devanagari(text: str) -> bool:
    return bool(re.search(r'[ऀ-ॿ]', text))


def _has_arabic_script(text: str) -> bool:
    return bool(re.search(r'[\u0600-\u06FF]', text))


def _translate_sync(text: str, target: str = 'hi') -> str:
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
            result = GoogleTranslator(source='en', target=target).translate(stripped)
            if result:
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
    translated_note = await loop.run_in_executor(None, lambda: _translate_sync(note_text, 'hi'))

    if not _has_devanagari(translated_note):
        log.warning("Translation produced no Devanagari — keeping English")
        return note_text, title

    translated_title = title
    if has_title and title:
        translated_title = await loop.run_in_executor(None, lambda: _translate_sync(title, 'hi'))
        if not _has_devanagari(translated_title):
            translated_title = title

    return translated_note, translated_title


async def translate_to_arabic(
    note_text: str,
    title: str | None,
    has_title: bool,
) -> tuple[str, str | None]:
    """Translate a note body (and optionally title) to Arabic script (Modern Standard Arabic).

    Returns (translated_body, translated_title).
    Falls back to English text if translation fails.
    Numerals: randomly keeps Arabic-Indic (٠١٢٣٤٥٦٧٨٩) 50% of time, Western digits otherwise.
    """
    import random
    loop = asyncio.get_event_loop()
    translated_note = await loop.run_in_executor(None, lambda: _translate_sync(note_text, 'ar'))

    if not _has_arabic_script(translated_note):
        log.warning("Translation produced no Arabic script — keeping English")
        return note_text, title

    # Mix numerals: 50% keep Arabic-Indic, 50% convert back to Western digits
    translated_note = _mix_arabic_numerals(translated_note)

    translated_title = title
    if has_title and title:
        translated_title = await loop.run_in_executor(None, lambda: _translate_sync(title, 'ar'))
        if not _has_arabic_script(translated_title):
            translated_title = title
        else:
            translated_title = _mix_arabic_numerals(translated_title)

    return translated_note, translated_title


# Arabic-Indic to Western digit map
_ARABIC_INDIC_TO_WESTERN = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')


def _mix_arabic_numerals(text: str) -> str:
    """Randomly keep Arabic-Indic numerals OR convert to Western digits.

    50% chance per note: keeps ٣٠ as-is (Arabic-Indic)
    50% chance per note: converts ٣٠ → 30 (Western)
    This creates realistic mixed-numeral variety across a batch.
    """
    import random
    if random.random() < 0.5:
        # Convert Arabic-Indic numerals to Western digits
        return text.translate(_ARABIC_INDIC_TO_WESTERN)
    # Keep as-is (Arabic-Indic numerals stay)
    return text

