"""Resolución determinista de intención y géneros desde el prompt."""

from __future__ import annotations

import re

from cadence.music.genre_catalog import all_genres, normalize_genre, normalize_genres
from cadence.schemas.song_state import CreativeBrief, UserIntent

_BPM_RE = re.compile(r"\b(\d{2,3})\s*bpm\b", re.IGNORECASE)

_USE_CASE_MARKERS: tuple[tuple[str, str], ...] = (
    ("cutscene", "cutscene"),
    ("cinemática", "cutscene"),
    ("diálogo", "cutscene"),
    ("loop", "loop"),
    ("overworld", "loop"),
    ("exploración", "loop"),
    ("animación", "animation"),
    ("animation", "animation"),
    ("trailer", "animation"),
)

_MOOD_MARKERS: tuple[tuple[str, str], ...] = (
    ("melanchol", "melancholic"),
    ("triste", "melancholic"),
    ("sad", "melancholic"),
    ("calm", "calm"),
    ("tranquil", "calm"),
    ("peaceful", "calm"),
    ("dark", "dark"),
    ("oscuro", "dark"),
    ("aggressive", "aggressive"),
    ("agresiv", "aggressive"),
    ("intense", "intense"),
    ("épico", "epic"),
    ("epic", "epic"),
    ("heroic", "heroic"),
    ("mysterious", "mysterious"),
    ("misterios", "mysterious"),
    ("tense", "tense"),
    ("tensión", "tense"),
    ("energetic", "energetic"),
    ("energétic", "energetic"),
)

_TECHNICAL_MARKERS = (
    "bpm", "compás", "compas", "time signature", "4/4", "3/4",
    "minor", "major", "tonalidad", "key of", "progresión", "progression",
    "intro-verse", "intro-verse-chorus",
)


def extract_bpm_from_prompt(raw_prompt: str) -> int | None:
    m = _BPM_RE.search(raw_prompt or "")
    if m:
        val = int(m.group(1))
        if 40 <= val <= 220:
            return val
    return None


def has_explicit_technical_params(raw_prompt: str) -> bool:
    """True si el prompt menciona parámetros musicales explícitos."""
    p = (raw_prompt or "").lower()
    if extract_bpm_from_prompt(p):
        return True
    from cadence.music.tonal_policy import parse_explicit_key_mode

    if parse_explicit_key_mode(p):
        return True
    return any(m in p for m in _TECHNICAL_MARKERS)


def resolve_use_case(raw_prompt: str) -> str:
    p = (raw_prompt or "").lower()
    for marker, uc in _USE_CASE_MARKERS:
        if marker in p:
            return uc
    if any(x in p for x in ("boss", "jefe", "combate", "fight", "battle", "nivel", "level")):
        return "game"
    return "game"


def resolve_mood(raw_prompt: str) -> str:
    p = (raw_prompt or "").lower()
    for marker, mood in _MOOD_MARKERS:
        if marker in p:
            return mood
    return "intense" if any(x in p for x in ("boss", "fight", "battle")) else "dark"


def genres_from_prompt(
    raw_prompt: str,
    *,
    extra_tags: list[str] | None = None,
    max_count: int = 8,
) -> list[str]:
    """Géneros canónicos cuyo id aparece en el prompt (orden estable)."""
    p = (raw_prompt or "").lower()
    found: list[str] = []
    seen: set[str] = set()
    for genre in all_genres():
        gl = genre.lower()
        if gl in p and gl not in seen:
            seen.add(gl)
            found.append(genre)
    for tag in extra_tags or []:
        norm = normalize_genre(tag)
        key = norm.lower()
        if key and key not in seen:
            seen.add(key)
            found.append(norm)
    return normalize_genres(found, max_count=max_count)


def resolve_intent_from_prompt(
    raw_prompt: str,
    *,
    llm_style_tags: list[str] | None = None,
    creative_brief: CreativeBrief | None = None,
) -> UserIntent:
    """Construye UserIntent sin LLM; integra brief dramático si existe."""
    from cadence.music.creative_brief import combined_prompt_text

    combined = combined_prompt_text(raw_prompt, creative_brief)
    extra = list(llm_style_tags or [])
    if creative_brief:
        extra.extend(creative_brief.style_hints)
        extra.extend(creative_brief.mood_keywords)

    tags = genres_from_prompt(combined, extra_tags=extra)
    kl = "technical" if has_explicit_technical_params(raw_prompt) else "non_technical"

    use_case = creative_brief.use_case if creative_brief else resolve_use_case(raw_prompt)
    if creative_brief and creative_brief.mood_keywords:
        mood = creative_brief.mood_keywords[0].strip().lower()
    else:
        mood = resolve_mood(combined)

    return UserIntent(
        raw_prompt=raw_prompt.strip(),
        knowledge_level=kl,
        use_case=use_case,  # type: ignore[arg-type]
        mood=mood,
        style_tags=tags[:6] if tags else ["video game music"],
    )
