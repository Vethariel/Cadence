"""Perfil de estilo determinista desde prompt y géneros del catálogo."""

from __future__ import annotations

from cadence.music.genre_catalog import normalize_genres
from cadence.music.prompt_resolve import genres_from_prompt
from cadence.music.style_profile import sanitize_style_references
from cadence.schemas.song_state import MusicalStyleProfile, UserIntent

_AVOID_BY_GENRE: dict[str, list[str]] = {
    "dubstep": ["calliope", "music box", "orchestral strings pad"],
    "techno": ["calliope", "music box"],
    "chiptune": ["orchestral strings pad", "brass section"],
    "boss fight": ["music box", "lullaby"],
}

_DRUM_CHARACTER: dict[str, str] = {
    "techno": "four-on-floor kick",
    "dubstep": "half-time dubstep groove",
    "house": "four-on-floor house",
    "chiptune": "square pulse drums",
    "orchestral": "orchestral percussion hits",
    "boss fight": "driving combat pulse",
}


def _references_from_prompt(raw_prompt: str, genres: list[str]) -> list[str]:
    """Nombres propios entre comillas o patrones OST/juego (heurística simple)."""
    import re

    refs: list[str] = []
    for m in re.finditer(r'"([^"]{2,40})"|\'([^\']{2,40})\'', raw_prompt):
        ref = (m.group(1) or m.group(2) or "").strip()
        if ref:
            refs.append(ref)
    return sanitize_style_references(refs, genres)


def build_style_profile_deterministic(
    intent: UserIntent,
    *,
    proposal_genres: list[str] | None = None,
) -> MusicalStyleProfile:
    """Perfil sin LLM: géneros del catálogo + heurísticas de prompt."""
    genres = genres_from_prompt(
        intent.raw_prompt,
        extra_tags=(proposal_genres or []) + intent.style_tags,
        max_count=8,
    )
    genres = normalize_genres(genres)

    avoid: list[str] = []
    for g in genres:
        for term in _AVOID_BY_GENRE.get(g, []):
            if term not in avoid:
                avoid.append(term)
    p = intent.raw_prompt.lower()
    if "sin batería" in p or "no drums" in p or "without drums" in p:
        avoid.append("drums")
    if "compact" in p or "pocos instrumentos" in p:
        avoid.extend(["orchestral strings pad", "full orchestra"])

    drum = ""
    for g in genres:
        if g in _DRUM_CHARACTER:
            drum = _DRUM_CHARACTER[g]
            break

    refs = _references_from_prompt(intent.raw_prompt, genres)
    reasoning = (
        f"Perfil determinista: {len(genres)} géneros del catálogo "
        f"para use_case={intent.use_case}, mood={intent.mood}."
    )

    return MusicalStyleProfile(
        genres=genres,
        references=refs,
        instrumentation=[],
        avoid=avoid,
        drum_character=drum,
        reasoning=reasoning,
    )
