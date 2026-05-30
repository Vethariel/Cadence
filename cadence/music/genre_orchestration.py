"""Capas opcionales y presupuesto guiados por género — con guardrails narrativos."""

from __future__ import annotations

from cadence.music.style_profile import GenreMix, build_genre_mix

# Peso por capa según tokens de género (suma ponderada).
OPTIONAL_LAYER_GENRE_WEIGHTS: dict[str, dict[str, float]] = {
    "chiptune": {"arp_synth": 3.0, "synth_pluck": 2.5, "echo_synth": 2.0, "countermelody": 1.5},
    "eurobeat": {"arp_synth": 2.5, "synth_pluck": 2.0, "countermelody": 2.0},
    "arcade": {"arp_synth": 2.5, "countermelody": 2.0, "perc_aux": 1.5},
    "techno": {"chord_stab": 2.5, "perc_aux": 2.0, "arp_synth": 1.5},
    "dubstep": {"chord_stab": 3.0, "perc_aux": 2.5, "echo_synth": 2.0},
    "orchestral": {"pad": 3.0, "countermelody": 2.5, "chord_stab": 2.0, "arp_synth": 1.5},
    "cinematic": {"pad": 3.0, "countermelody": 2.5, "chord_stab": 1.5},
    "epic": {"pad": 2.5, "countermelody": 2.5, "perc_aux": 2.0, "chord_stab": 2.0},
    "boss fight": {"countermelody": 3.0, "chord_stab": 2.5, "perc_aux": 2.5, "arp_synth": 2.0},
    "ambient": {"pad": 3.0, "echo_synth": 2.5},
    "loop": {"pad": 3.0, "echo_synth": 2.0},
}

LEAD_FALLBACK_POOLS: dict[str, list[str]] = {
    "loop": ["pad", "echo_synth"],
    "cutscene": ["pad", "countermelody", "echo_synth"],
    "boss": ["countermelody", "chord_stab", "arp_synth", "perc_aux", "pad"],
    "dance": ["arp_synth", "synth_pluck", "echo_synth", "countermelody", "chord_stab"],
    "compact": ["countermelody", "chord_stab", "arp_synth"],
    "game_low": ["countermelody", "pad"],
    "game_mid": ["arp_synth", "countermelody", "chord_stab"],
    "game_high": ["arp_synth", "echo_synth", "countermelody", "chord_stab", "synth_pluck"],
    "default": ["arp_synth", "countermelody", "chord_stab"],
}


def _tags_from_inputs(
    genre_tags: list[str] | None,
    genre_mix: GenreMix | None,
) -> set[str]:
    out: set[str] = set()
    if genre_mix:
        out.update(genre_mix.keys())
    for t in genre_tags or []:
        out.add(t.lower().strip())
    return out


def optional_layer_genre_score(
    instrument_id: str,
    *,
    genre_tags: list[str] | None = None,
    genre_mix: GenreMix | None = None,
    composition_archetype: str | None = None,
    energy_level: int = 3,
) -> float:
    """Mayor = más alineado al género; capas sin match reciben score base bajo."""
    from cadence.music.genre_catalog import category_mix_from_genre_mix, category_mix_from_genres

    tags = _tags_from_inputs(genre_tags, genre_mix)
    score = 1.0
    from cadence.music.composition_archetypes import normalize_archetype

    arch = normalize_archetype(composition_archetype or "")
    cat_mix = category_mix_from_genre_mix(genre_mix or {}) or category_mix_from_genres(
        list(tags),
    )
    if arch == "orchestral_boss":
        cat_mix = {**cat_mix, "orchestral_cinematic": cat_mix.get("orchestral_cinematic", 0) + 0.4}
    if arch == "dense_dance":
        cat_mix = {**cat_mix, "synth_retro_game": cat_mix.get("synth_retro_game", 0) + 0.4}
    from cadence.music.genre_category_patterns import category_score_optional_layer

    score += category_score_optional_layer(instrument_id, cat_mix)

    for genre, weight in (genre_mix or {}).items():
        layer_w = OPTIONAL_LAYER_GENRE_WEIGHTS.get(genre, {}).get(instrument_id, 0)
        score += weight * layer_w * 0.65
    for genre, table in OPTIONAL_LAYER_GENRE_WEIGHTS.items():
        if genre in tags:
            score += table.get(instrument_id, 0) * 0.5
    if energy_level >= 4 and instrument_id in ("arp_synth", "chord_stab", "perc_aux"):
        score += 0.5
    if energy_level <= 2 and instrument_id in ("pad", "echo_synth"):
        score += 1.0
    return score


def adjust_optional_budget(
    max_optional: int,
    max_lead: int,
    *,
    genre_tags: list[str] | None = None,
    genre_mix: GenreMix | None = None,
    composition_archetype: str | None = None,
    energy_level: int = 3,
    use_case: str = "game",
) -> tuple[int, int]:
    """Ajusta presupuesto sin romper guardrails compactos."""
    from cadence.music.composition_archetypes import normalize_archetype, suppresses_ensemble

    tags = _tags_from_inputs(genre_tags, genre_mix)
    arch = normalize_archetype(composition_archetype or "")
    uc = (use_case or "game").lower()
    opt, lead = max_optional, max_lead

    if arch in ("compact_action", "energetic_game"):
        return min(opt, 3), min(lead, 2 if arch == "energetic_game" else 1)
    if arch == "orchestral_boss" and energy_level >= 4:
        opt = min(opt + 1, 5)
        lead = min(lead + 1, 3)
    elif arch == "dense_dance" and energy_level >= 4:
        opt = min(opt, 4)
        lead = min(lead + 1, 3)
    elif (
        tags & {"orchestral", "cinematic", "epic"}
        and energy_level >= 4
        and not suppresses_ensemble(arch)
    ):
        opt = min(opt + 1, 5)
        lead = min(lead + 1, 3)
    elif tags & {"chiptune", "techno", "dubstep"} and energy_level >= 4:
        lead = min(lead + 1, 3)

    if uc == "loop":
        opt = min(opt, 1)
        lead = 0
    elif uc == "cutscene":
        opt = min(opt, 2)
        lead = min(lead, 1)

    return opt, lead


def lead_fallback_pool(
    *,
    use_case: str,
    energy_level: int,
    composition_archetype: str | None = None,
    genre_tags: list[str] | None = None,
    genre_mix: GenreMix | None = None,
) -> list[str]:
    from cadence.music.rhythm_fallback_ladders import resolve_rhythm_context_key

    key = resolve_rhythm_context_key(
        use_case=use_case,
        energy_level=energy_level,
        composition_archetype=composition_archetype,
        genre_tags=genre_tags,
        genre_mix=genre_mix,
    )
    return list(LEAD_FALLBACK_POOLS.get(key, LEAD_FALLBACK_POOLS["default"]))


def _pick_scored(seed: int, salt: int, candidates: list[str], weights: dict[str, float]) -> str:
    jitter = (seed * 31 + salt * 17) % 10_000
    total = sum(weights.get(c, 1.0) for c in candidates)
    if total <= 0:
        return candidates[jitter % len(candidates)]
    target = (jitter / 10_000.0) * total
    acc = 0.0
    for c in candidates:
        acc += weights.get(c, 1.0)
        if target < acc:
            return c
    return candidates[-1]


def select_lead_layers_genre_aware(
    *,
    use_case: str,
    energy_level: int,
    generation_seed: int,
    composition_archetype: str | None = None,
    genre_tags: list[str] | None = None,
    genre_mix: GenreMix | None = None,
    max_lead: int = 2,
) -> set[str]:
    """Elige capas lead opcionales con pool y pesos por género."""
    from cadence.music.instrument_catalog import MAX_LEAD_OPTIONALS

    uc = (use_case or "game").lower()
    cap = min(max_lead, MAX_LEAD_OPTIONALS.get(uc, 2))
    if cap <= 0:
        return set()

    mix = genre_mix or build_genre_mix(proposal_tags=genre_tags or [])
    pool = lead_fallback_pool(
        use_case=use_case,
        energy_level=energy_level,
        composition_archetype=composition_archetype,
        genre_tags=genre_tags,
        genre_mix=mix,
    )
    weights = {
        lid: optional_layer_genre_score(
            lid,
            genre_tags=genre_tags,
            genre_mix=mix,
            composition_archetype=composition_archetype,
            energy_level=energy_level,
        )
        for lid in pool
    }
    chosen: set[str] = set()
    for i in range(cap):
        remaining = [p for p in pool if p not in chosen]
        if not remaining:
            break
        chosen.add(_pick_scored(generation_seed, 29 + i * 7, remaining, weights))
    return chosen
