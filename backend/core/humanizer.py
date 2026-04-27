"""Humanizer — Pass B: Post-process notes with a different LLM to break AI fingerprint."""

import random
import logging

log = logging.getLogger(__name__)


HUMANIZE_SYSTEM = """You are editing a short phone note. Make tiny changes only.

RULES:
- Change 1-2 words to synonyms or rephrase slightly
- Maybe add or fix one typo
- Keep EVERY line break exactly as-is. Do NOT merge lines.
- Keep the same length (±3 words)
- Do NOT add new content or make it longer
- Do NOT change names or relationships
- Do NOT add punctuation, em dashes, or semicolons
- Do NOT add a conclusion or summary

Output ONLY the edited note. Same line count, same format."""


async def humanize_note(llm_clients, note: str, persona: dict) -> str:
    """Run Pass B humanization. Skipped ~30% of the time."""
    # 30% chance to skip humanization entirely
    if random.random() < 0.30:
        log.debug("Skipping humanization (30%% random skip)")
        return note

    line_count = len([l for l in note.split('\n') if l.strip()])

    user_prompt = f"""Edit this {line_count}-line phone note. Keep exactly {line_count} lines:

{note}

Output ONLY the edited note. Keep {line_count} lines."""

    try:
        result = await llm_clients.generate(
            system_prompt=HUMANIZE_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.8,
            max_tokens=200,
            provider="gemini",
        )
        # Clean up
        result = result.strip().strip('"').strip("'")
        if result.startswith("```"):
            result = result.split("```")[1] if "```" in result[3:] else result[3:]
            result = result.strip()

        # Safety: if humanizer merged everything into fewer lines, keep original
        result_lines = len([l for l in result.split('\n') if l.strip()])
        if result_lines < line_count - 1:
            log.warning("Humanizer merged lines (%d -> %d), keeping original", line_count, result_lines)
            return note

        return result
    except Exception as e:
        log.warning("Humanization failed: %s, using original note", e)
        return note
