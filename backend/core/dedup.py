"""Dedup engine — ensures unique entries via registry + embedding similarity."""

import logging
import re
import numpy as np
from typing import Optional

log = logging.getLogger(__name__)

# Lazy-loaded sentence transformer
_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('all-MiniLM-L6-v2')
        log.info("Loaded sentence-transformers model: all-MiniLM-L6-v2")
    return _model


def normalize_title(title: Optional[str]) -> str:
    """Normalize a title for dedup comparison."""
    if not title:
        return ""
    title = title.lower().strip()
    title = re.sub(r'[^\w\s]', '', title)
    title = re.sub(r'\s+', ' ', title)
    return title


def get_opening_trigram(text: str) -> str:
    """Extract the first 3 words of the body (after title if present)."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    # Use first body line (skip title)
    body_start = lines[0] if lines else ""
    words = body_start.split()[:3]
    return ' '.join(words).lower()


def compute_embedding(text: str) -> np.ndarray:
    """Compute embedding vector for a note text."""
    model = _get_model()
    return model.encode(text, normalize_embeddings=True)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two normalized vectors."""
    return float(np.dot(a, b))


def check_embedding_uniqueness(
    new_embedding: np.ndarray,
    existing_embeddings: list[bytes],
    threshold: float = 0.78,
) -> tuple[bool, float]:
    """Check that new embedding is sufficiently different from all existing ones.
    
    Returns (is_unique, max_similarity).
    """
    if not existing_embeddings:
        return True, 0.0

    max_sim = 0.0
    for emb_bytes in existing_embeddings:
        existing = np.frombuffer(emb_bytes, dtype=np.float32)
        sim = cosine_similarity(new_embedding, existing)
        max_sim = max(max_sim, sim)
        if sim > threshold:
            return False, sim

    return True, max_sim


def title_jaccard_similarity(title1: str, title2: str) -> float:
    """Compute Jaccard similarity between two title word sets."""
    if not title1 or not title2:
        return 0.0
    words1 = set(title1.lower().split())
    words2 = set(title2.lower().split())
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union)


async def check_all_dedup(
    db,
    note_text: str,
    full_name: str,
    title: Optional[str],
    has_title: bool,
    relationship: str,
    topic: str,
    mood: str,
) -> tuple[bool, str, Optional[np.ndarray]]:
    """Run all dedup checks. Returns (passed, reason, embedding)."""

    # 1. Unique full name
    if await db.check_name_exists(full_name):
        return False, f"Duplicate name: {full_name}", None

    # 2. Unique normalized title (or first line)
    norm_title = normalize_title(title) if has_title else normalize_title(
        note_text.split('\n')[0] if note_text else ""
    )
    if norm_title and await db.check_title_exists(norm_title):
        return False, f"Duplicate title: {norm_title}", None

    # 3. Unique opening 3-gram
    # Get body text (skip title line if present)
    lines = [l.strip() for l in note_text.split('\n') if l.strip()]
    body_lines = lines[1:] if has_title and len(lines) > 1 else lines
    body_text = body_lines[0] if body_lines else ""
    trigram = get_opening_trigram(body_text)
    if trigram and await db.check_trigram_exists(trigram):
        return False, f"Duplicate opening trigram: {trigram}", None

    # 4. (relationship × topic × mood) capped at 3
    combo = f"{relationship}|{topic}|{mood}"
    combo_count = await db.count_combo(combo)
    if combo_count >= 3:
        return False, f"Combo used {combo_count} times: {combo}", None

    # 5. Embedding cosine similarity ≤ 0.78
    embedding = compute_embedding(note_text)
    existing_embeddings = await db.get_all_embeddings()
    is_unique, max_sim = check_embedding_uniqueness(embedding, existing_embeddings)
    if not is_unique:
        return False, f"Too similar to existing note (cosine={max_sim:.3f})", None

    # 6. Title Jaccard ≤ 0.6 vs last 50
    if has_title and norm_title:
        recent_titles = await db.get_recent_titles(50)
        for rt in recent_titles:
            jacc = title_jaccard_similarity(norm_title, rt)
            if jacc > 0.6:
                return False, f"Title too similar (Jaccard={jacc:.2f}): {rt}", None

    return True, "Unique", embedding
