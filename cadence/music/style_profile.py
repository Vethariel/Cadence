"""Helpers para MusicalStyleProfile — tags efectivos y evitar timbres."""

from __future__ import annotations

from cadence.music.genre_catalog import all_genres, normalize_genre, normalize_genres
from cadence.music.timbre_library import GM_PROGRAM_NAMES
from cadence.schemas.song_state import MusicalStyleProfile, SongState


def effective_genre_tags(state: SongState) -> list[str]:
    """Unión de géneros/referencias del perfil LLM + proposal; sin duplicados."""
    seen: set[str] = set()
    ordered: list[str] = []

    profile = state.get("style_profile")
    if profile:
        for tag in profile.genres + profile.references:
            key = tag.lower().strip()
            if key and key not in seen:
                seen.add(key)
                ordered.append(tag.strip())

    proposal = state.get("technical_proposal")
    if proposal:
        for tag in proposal.genre_tags:
            key = tag.lower().strip()
            if key and key not in seen:
                seen.add(key)
                ordered.append(tag.strip())

    if not ordered:
        intent = state.get("intent")
        if intent:
            ordered = list(intent.style_tags)

    return ordered


def sanitize_style_references(
    references: list[str],
    genres: list[str],
) -> list[str]:
    """
    Quita entradas que son géneros del catálogo o duplican `genres`.
    references solo debe llevar nombres propios del prompt (juegos, artistas, OST).
    """
    if not references:
        return []
    genre_keys = {normalize_genre(g).lower() for g in genres}
    catalog_keys = {g.lower() for g in all_genres()}
    seen: set[str] = set()
    out: list[str] = []
    for ref in references:
        raw = ref.strip()
        if not raw:
            continue
        key = raw.lower()
        if key in seen:
            continue
        if key in genre_keys:
            continue
        if normalize_genre(raw).lower() in genre_keys:
            continue
        if key in catalog_keys:
            continue
        if normalize_genre(raw).lower() in catalog_keys:
            continue
        seen.add(key)
        out.append(raw)
    return out


def format_profile_for_llm(profile: MusicalStyleProfile | None) -> str:
    if not profile:
        return "(sin perfil de estilo enriquecido)"
    lines = [
        "=== PERFIL DE ESTILO (LLM) ===",
        f"Géneros: {', '.join(profile.genres) or '—'}",
        f"Referentes: {', '.join(profile.references) or '—'}",
        f"Instrumentación deseada: {', '.join(profile.instrumentation) or '—'}",
        f"Evitar: {', '.join(profile.avoid) or '—'}",
    ]
    if profile.drum_character:
        lines.append(f"Carácter rítmico: {profile.drum_character}")
    if profile.reasoning:
        lines.append(f"Razonamiento: {profile.reasoning}")
    return "\n".join(lines)


def programs_matching_avoid(avoid_terms: list[str]) -> set[int]:
    """Mapea términos de evitar a gm_program por nombre GM."""
    if not avoid_terms:
        return set()
    terms = [t.lower().strip() for t in avoid_terms if t.strip()]
    bad: set[int] = set()
    for program, name in GM_PROGRAM_NAMES.items():
        n = name.lower()
        n_compact = n.replace(" ", "")
        matched = False
        for term in terms:
            if term in n or term.replace(" ", "") in n_compact:
                matched = True
                break
            for word in term.split():
                if len(word) >= 4 and word in n:
                    matched = True
                    break
            if matched:
                break
        if matched:
            bad.add(program)
    return bad


def merge_proposal_genre_tags(
    proposal_tags: list[str],
    profile: MusicalStyleProfile | None,
) -> list[str]:
    """Prioriza géneros del perfil enriquecido sobre tags genéricos del proposal."""
    if not profile or not profile.genres:
        return normalize_genres(proposal_tags)
    seen = {t.lower() for t in profile.genres}
    merged = list(profile.genres)
    for tag in proposal_tags:
        norm = normalize_genre(tag)
        if norm.lower() not in seen:
            merged.append(norm)
            seen.add(norm.lower())
    return normalize_genres(merged)
