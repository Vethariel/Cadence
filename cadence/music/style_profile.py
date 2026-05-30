"""Helpers para MusicalStyleProfile — tags efectivos, genre_mix y evitar timbres."""

from __future__ import annotations

from collections import defaultdict

from cadence.music.genre_catalog import all_genres, normalize_genre, normalize_genres
from cadence.music.timbre_library import GM_PROGRAM_NAMES
from cadence.schemas.song_state import MusicalStyleProfile, SongState

GenreMix = dict[str, float]

_PROFILE_SOURCE_WEIGHT = 1.0
_PROPOSAL_SOURCE_WEIGHT = 0.75
_PROMPT_KEYWORD_WEIGHT = 0.9
_MAX_DOMINANT_SHARE = 0.38
_MIN_ACTIVE_GENRE_WEIGHT = 0.08

_PROMPT_GENRE_HINTS: tuple[tuple[str, str], ...] = (
    ("boss fight", "boss fight"),
    ("final boss", "boss fight"),
    ("boss battle", "boss fight"),
    ("orchestral", "orchestral"),
    ("orquesta", "orchestral"),
    ("symphonic", "symphonic"),
    ("cinematic", "cinematic"),
    ("epic", "epic"),
    ("techno", "techno"),
    ("dubstep", "dubstep"),
    ("chiptune", "chiptune"),
    ("eurobeat", "eurobeat"),
    ("arcade", "arcade"),
    ("industrial", "industrial"),
    ("house", "house"),
    ("hybrid orchestral", "hybrid orchestral"),
)


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


def _normalize_mix_key(tag: str) -> str:
    return normalize_genre(tag.strip()).lower()


def _accumulate_mix(weights: dict[str, float], tag: str, amount: float) -> None:
    key = _normalize_mix_key(tag)
    if key:
        weights[key] += amount


def _normalize_mix(weights: dict[str, float]) -> GenreMix:
    if not weights:
        return {}
    total = sum(weights.values())
    if total <= 0:
        return {}
    return {g: round(w / total, 4) for g, w in weights.items()}


def balance_genre_mix(mix: GenreMix, *, max_dominant: float = _MAX_DOMINANT_SHARE) -> GenreMix:
    """
    Evita que un solo género acapare el mix cuando hay varios activos
    (p. ej. techno + orchestral + boss fight).
    """
    if len(mix) < 2:
        return mix
    top_genre = max(mix, key=mix.get)
    top_w = mix[top_genre]
    if top_w <= max_dominant:
        return mix
    others = {g: w for g, w in mix.items() if g != top_genre}
    active_others = [g for g, w in others.items() if w >= _MIN_ACTIVE_GENRE_WEIGHT]
    if len(active_others) < 1:
        return mix
    capped = dict(mix)
    capped[top_genre] = max_dominant
    remainder = 1.0 - max_dominant
    other_sum = sum(others[g] for g in active_others)
    if other_sum <= 0:
        share = remainder / len(active_others)
        for g in active_others:
            capped[g] = round(share, 4)
    else:
        for g in active_others:
            capped[g] = round(remainder * (others[g] / other_sum), 4)
    inactive = [g for g in capped if g not in active_others and g != top_genre]
    for g in inactive:
        capped[g] = round(capped[g] * 0.5, 4)
    return _normalize_mix(capped)


def build_genre_mix(
    *,
    style_profile: MusicalStyleProfile | None = None,
    proposal_tags: list[str] | None = None,
    intent_tags: list[str] | None = None,
    raw_prompt: str = "",
) -> GenreMix:
    """Construye genre_mix ponderado desde perfil, proposal, intent y prompt."""
    weights: dict[str, float] = defaultdict(float)

    if style_profile and style_profile.genres:
        share = _PROFILE_SOURCE_WEIGHT / len(style_profile.genres)
        for g in style_profile.genres:
            _accumulate_mix(weights, g, share)

    if proposal_tags:
        share = _PROPOSAL_SOURCE_WEIGHT / max(1, len(proposal_tags))
        for g in proposal_tags:
            _accumulate_mix(weights, g, share)

    if intent_tags:
        share = _PROPOSAL_SOURCE_WEIGHT * 0.5 / max(1, len(intent_tags))
        for g in intent_tags:
            _accumulate_mix(weights, g, share)

    prompt = (raw_prompt or "").lower()
    hits = [canonical for term, canonical in _PROMPT_GENRE_HINTS if term in prompt]
    if hits:
        share = _PROMPT_KEYWORD_WEIGHT / len(hits)
        for g in hits:
            _accumulate_mix(weights, g, share)

    mix = _normalize_mix(weights)
    if not mix and intent_tags:
        for g in normalize_genres(intent_tags):
            _accumulate_mix(weights, g, 1.0)
        mix = _normalize_mix(weights)
    return balance_genre_mix(mix)


def build_genre_mix_from_state(state: SongState) -> GenreMix:
    intent = state.get("intent")
    proposal = state.get("technical_proposal")
    return build_genre_mix(
        style_profile=state.get("style_profile"),
        proposal_tags=proposal.genre_tags if proposal else None,
        intent_tags=intent.style_tags if intent else None,
        raw_prompt=intent.raw_prompt if intent else "",
    )


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
