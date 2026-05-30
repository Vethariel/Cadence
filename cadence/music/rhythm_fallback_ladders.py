"""Escaleras de fallback rítmico por contexto — evita un único default (p. ej. root_fifth)."""

from __future__ import annotations

from cadence.music.pattern_registry import pattern_family
from cadence.music.style_profile import GenreMix, build_genre_mix

# Familias en orden de preferencia (sin sufijo _a/_b; se expanden al elegir).
DRUM_FALLBACK_LADDERS: dict[str, list[str]] = {
    "loop": ["default", "halftime", "house"],
    "cutscene": ["halftime", "default", "house"],
    "boss": ["breakbeat", "industrial", "dubstep", "techno"],
    "dance": ["techno", "breakbeat", "house", "dnb"],
    "compact": ["breakbeat", "techno", "house", "halftime"],
    "game_low": ["default", "halftime", "house"],
    "game_mid": ["house", "techno", "breakbeat", "default"],
    "game_high": ["techno", "breakbeat", "dubstep", "dnb", "industrial"],
    "default": ["default", "house", "techno", "breakbeat"],
}

BASS_FALLBACK_LADDERS: dict[str, list[str]] = {
    "loop": ["pulse", "half_time", "root_fifth"],
    "cutscene": ["pulse", "half_time", "root_fifth", "driving"],
    "boss": ["driving", "octave_pulse", "half_time", "syncopated", "walk"],
    "dance": ["octave_pulse", "driving", "syncopated", "staccato", "half_time"],
    "compact": ["driving", "syncopated", "pulse", "half_time"],
    "game_low": ["pulse", "half_time", "root_fifth"],
    "game_mid": ["driving", "syncopated", "half_time", "root_fifth"],
    "game_high": ["driving", "syncopated", "octave_pulse", "walk", "half_time", "staccato"],
    "default": ["driving", "syncopated", "half_time", "root_fifth", "pulse"],
}

def _category_mix(
    genre_tags: list[str] | None,
    genre_mix: GenreMix | None,
) -> dict[str, float]:
    from cadence.music.genre_catalog import category_mix_from_genre_mix, category_mix_from_genres

    if genre_mix:
        return category_mix_from_genre_mix(genre_mix)
    if genre_tags:
        return category_mix_from_genres(genre_tags)
    return {}


def resolve_rhythm_context_key(
    *,
    use_case: str,
    energy_level: int,
    composition_archetype: str | None = None,
    genre_tags: list[str] | None = None,
    genre_mix: GenreMix | None = None,
) -> str:
    """Clave de ladder: loop | cutscene | boss | dance | compact | game_* | default."""
    from cadence.music.genre_category_patterns import rhythm_ladder_bias_from_categories

    uc = (use_case or "game").lower()
    arch = composition_archetype or ""
    cat_mix = _category_mix(genre_tags, genre_mix)

    if uc == "loop":
        return "loop"
    if uc == "cutscene":
        return "cutscene"
    if arch == "orchestral_boss":
        return "boss"
    if arch == "chiptune_dance":
        return "dance"
    if arch == "compact_action":
        return "compact"

    cat_bias = rhythm_ladder_bias_from_categories(
        cat_mix, energy_level=energy_level,
    )
    if cat_bias:
        return cat_bias

    if energy_level <= 2:
        return "game_low"
    if energy_level >= 5:
        return "game_high"
    if energy_level >= 4:
        return "game_high"
    if energy_level == 3:
        return "game_mid"
    return "default"


def _expand_families(families: list[str], *, variant_suffix: str = "a") -> list[str]:
    """Convierte familias a IDs canónicos preferidos (half_time → half_time_a)."""
    out: list[str] = []
    for fam in families:
        parts = fam.rsplit("_", 1)
        if len(parts) == 2 and parts[1] in ("a", "b", "c"):
            out.append(fam)
        else:
            out.append(f"{fam}_{variant_suffix}")
    return out


def _merge_priority_and_ladder(
    priority: list[str],
    ladder_families: list[str],
) -> list[str]:
    """Union ordenada: prioridad de repertorio + ladder sin duplicar familias."""
    seen: set[str] = set()
    ordered: list[str] = []
    for pid in priority:
        fam = pattern_family(pid)
        if fam not in seen:
            seen.add(fam)
            ordered.append(pid)
    for fam in ladder_families:
        if fam not in seen:
            seen.add(fam)
            ordered.append(fam)
    return ordered


def fallback_drum_candidates(
    *,
    use_case: str,
    energy_level: int,
    composition_archetype: str | None = None,
    genre_tags: list[str] | None = None,
    genre_mix: GenreMix | None = None,
    repertoire_priority: list[str] | None = None,
) -> list[str]:
    key = resolve_rhythm_context_key(
        use_case=use_case,
        energy_level=energy_level,
        composition_archetype=composition_archetype,
        genre_tags=genre_tags,
        genre_mix=genre_mix,
    )
    ladder = DRUM_FALLBACK_LADDERS.get(key, DRUM_FALLBACK_LADDERS["default"])
    rep = list(repertoire_priority or [])
    if key in ("loop", "cutscene", "game_low"):
        allowed = set(ladder)
        rep = [p for p in rep if pattern_family(p) in allowed]
    merged = _merge_priority_and_ladder(rep, ladder)
    return _expand_families(
        [pattern_family(p) for p in merged],
        variant_suffix="a",
    )


def fallback_bass_candidates(
    *,
    use_case: str,
    energy_level: int,
    composition_archetype: str | None = None,
    genre_tags: list[str] | None = None,
    genre_mix: GenreMix | None = None,
    repertoire_priority: list[str] | None = None,
) -> list[str]:
    """
    Candidatos de bajo para fallback — root_fifth al final en contextos de alta energía.
    """
    key = resolve_rhythm_context_key(
        use_case=use_case,
        energy_level=energy_level,
        composition_archetype=composition_archetype,
        genre_tags=genre_tags,
        genre_mix=genre_mix,
    )
    ladder = list(BASS_FALLBACK_LADDERS.get(key, BASS_FALLBACK_LADDERS["default"]))
    if key in ("loop", "cutscene", "game_low"):
        allowed = set(ladder)
        repertoire_priority = [
            p for p in (repertoire_priority or [])
            if pattern_family(p) in allowed
        ]
    if key in ("game_high", "boss", "dance", "compact") and "root_fifth" in ladder:
        ladder = [f for f in ladder if f != "root_fifth"] + ["root_fifth"]
    merged = _merge_priority_and_ladder(repertoire_priority or [], ladder)
    return _expand_families(
        [pattern_family(p) for p in merged],
        variant_suffix="a",
    )


def build_genre_mix_for_rhythm(genre_tags: list[str] | None) -> GenreMix:
    if not genre_tags:
        return {}
    return build_genre_mix(proposal_tags=genre_tags)
