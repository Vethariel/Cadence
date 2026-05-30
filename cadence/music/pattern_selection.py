"""Muestreo ponderado determinista — pesos desde genre_mix, arquetipo y narrativa."""

from __future__ import annotations

from cadence.music.pattern_batch_context import get_batch_recent_patterns
from cadence.music.pattern_registry import expand_family_candidates, pattern_family

_BATCH_PENALTY = 0.12
_RECENT_WINDOW = 4

_ARCHETYPE_FIELD_BIAS: dict[str, dict[str, dict[str, float]]] = {
    "orchestral_boss": {
        "drum": {"breakbeat": 2.0, "industrial": 1.5, "dubstep": 1.2},
        "bass": {"half_time": 2.5, "root_fifth": 2.2, "pulse": 1.8, "syncopated": 1.2},
        "stab": {"orchestral_sync": 3.0},
        "counter": {"orchestral_sync": 2.5},
    },
    "chiptune_dance": {
        "drum": {"breakbeat": 2.0, "techno": 1.8, "dnb": 1.5},
        "arp": {"sixteenth": 2.5, "cascade": 2.0},
        "bass": {"octave_pulse": 2.5, "driving": 2.0},
    },
    "compact_action": {
        "drum": {"breakbeat": 2.0, "techno": 1.5},
        "bass": {"driving": 2.0, "syncopated": 1.5},
    },
}

_MOOD_FIELD_BIAS: dict[str, dict[str, dict[str, float]]] = {
    "dark": {"drum": {"industrial": 2.0, "dubstep": 1.5}, "harmony": {"dark": 2.5}},
    "epic": {
        "drum": {"breakbeat": 1.8, "industrial": 1.5},
        "harmony": {"cinematic": 2.0, "aggressive": 1.5},
        "stab": {"orchestral_sync": 2.0},
    },
    "tense": {"drum": {"breakbeat": 1.5}, "bass": {"syncopated": 1.8}},
    "energetic": {"drum": {"dnb": 1.8, "techno": 1.5}, "arp": {"sixteenth": 2.0}},
}


def _node_jitter(seed: int, salt: int) -> int:
    return abs(hash((seed, salt, "cadence_weighted_pick_v2"))) % 10_000


def _batch_weight_factor(choice_id: str, field: str, recent: list[str]) -> float:
    if not recent:
        return 1.0
    fam = pattern_family(choice_id)
    hits = 0
    for sig in recent[-_RECENT_WINDOW:]:
        if f"{field}:{choice_id}" in sig or f"{field}:{fam}" in sig:
            hits += 1
    if hits >= 2:
        return _BATCH_PENALTY
    if hits == 1:
        return 0.45
    return 1.0


def _apply_table_bias(
    weights: dict[str, float],
    candidate: str,
    table: dict[str, float],
    multiplier: float = 1.0,
) -> None:
    fam = pattern_family(candidate)
    for key, boost in table.items():
        if key == candidate or key == fam:
            weights[candidate] = weights.get(candidate, 0.0) + boost * multiplier


def compute_candidate_weights(
    candidates: list[str],
    *,
    genre_mix: dict[str, float] | None = None,
    genre_boost_table: dict[str, dict[str, float]] | None = None,
    composition_archetype: str | None = None,
    mood: str = "",
    energy_level: int = 3,
    field: str = "pattern",
    recent: list[str] | None = None,
) -> dict[str, float]:
    """Pesos por candidato antes del muestreo determinista."""
    if not candidates:
        return {}

    batch_recent = recent if recent is not None else get_batch_recent_patterns()
    weights: dict[str, float] = {}

    for rank, pid in enumerate(candidates):
        base = max(3.0, 16.0 - rank * 1.75)
        if energy_level >= 5 and field in ("drum", "bass", "arp"):
            base += 1.5
        weights[pid] = base * _batch_weight_factor(pid, field, batch_recent)

    if genre_mix and genre_boost_table:
        for genre, g_weight in genre_mix.items():
            if g_weight <= 0:
                continue
            boosts = genre_boost_table.get(genre, {})
            for pid in candidates:
                fam = pattern_family(pid)
                for key, boost in boosts.items():
                    if key == pid or key == fam:
                        weights[pid] = weights.get(pid, 0.0) + g_weight * boost

    if genre_mix:
        from cadence.music.genre_catalog import category_mix_from_genre_mix
        from cadence.music.genre_category_patterns import apply_category_boosts

        cat_mix = category_mix_from_genre_mix(genre_mix)
        apply_category_boosts(weights, candidates, field, cat_mix)

    arch = composition_archetype or ""
    arch_table = _ARCHETYPE_FIELD_BIAS.get(arch, {}).get(field, {})
    for pid in candidates:
        _apply_table_bias(weights, pid, arch_table, multiplier=2.0)

    m = (mood or "").lower()
    for token, mood_tables in _MOOD_FIELD_BIAS.items():
        if token in m:
            for pid in candidates:
                _apply_table_bias(
                    weights, pid, mood_tables.get(field, {}), multiplier=1.5,
                )

    if field == "bass" and composition_archetype:
        from cadence.music.voice_register_profile import (
            BASS_BY_TIER,
            resolve_voice_register_profile,
        )

        tier = resolve_voice_register_profile(
            composition_archetype=composition_archetype,
            energy_level=energy_level,
        ).bass_grid_tier
        allowed = set(BASS_BY_TIER.get(tier, ()))
        for pid in candidates:
            fam = pattern_family(pid)
            if fam in allowed or pid in allowed:
                weights[pid] = weights.get(pid, 0.0) + 2.5
            elif allowed:
                weights[pid] = weights.get(pid, 1.0) * 0.25

    for pid in candidates:
        weights.setdefault(pid, 1.0)
    return weights


def _weighted_pick_core(
    seed: int,
    salt: int,
    candidates: list[str],
    pool: tuple[str, ...] | list[str],
    *,
    genre_mix: dict[str, float] | None = None,
    genre_boost_table: dict[str, dict[str, float]] | None = None,
    composition_archetype: str | None = None,
    mood: str = "",
    energy_level: int = 3,
    field: str = "pattern",
    recent: list[str] | None = None,
) -> tuple[str, list[str], dict[str, float], int, float]:
    expanded = expand_family_candidates(candidates, pool)
    if not expanded:
        pool_tuple = tuple(pool)
        fallback = pool_tuple[0] if pool_tuple else ""
        return fallback, list(pool_tuple), {}, 0, 0.0

    weights = compute_candidate_weights(
        expanded,
        genre_mix=genre_mix,
        genre_boost_table=genre_boost_table,
        composition_archetype=composition_archetype,
        mood=mood,
        energy_level=energy_level,
        field=field,
        recent=recent,
    )

    jitter = _node_jitter(seed, salt)
    total = sum(weights.get(p, 1.0) for p in expanded)
    if total <= 0:
        chosen = expanded[jitter % len(expanded)]
        return chosen, expanded, weights, jitter, 0.0

    target = (jitter % 10_000) / 10_000.0 * total
    acc = 0.0
    chosen = expanded[-1]
    for pid in expanded:
        acc += weights.get(pid, 1.0)
        if target < acc:
            chosen = pid
            break
    target_ratio = target / total if total else 0.0
    return chosen, expanded, weights, jitter, target_ratio


def weighted_pick(
    seed: int,
    salt: int,
    candidates: list[str],
    pool: tuple[str, ...] | list[str],
    *,
    genre_mix: dict[str, float] | None = None,
    genre_boost_table: dict[str, dict[str, float]] | None = None,
    composition_archetype: str | None = None,
    mood: str = "",
    energy_level: int = 3,
    field: str = "pattern",
    recent: list[str] | None = None,
) -> str:
    """
    Muestreo ponderado determinista por seed (no seed % len).
    Expande familias del priority list a sub-variantes en pool.
    """
    chosen, _, _, _, _ = _weighted_pick_core(
        seed, salt, candidates, pool,
        genre_mix=genre_mix,
        genre_boost_table=genre_boost_table,
        composition_archetype=composition_archetype,
        mood=mood,
        energy_level=energy_level,
        field=field,
        recent=recent,
    )
    return chosen


def weighted_pick_audited(
    seed: int,
    salt: int,
    candidates: list[str],
    pool: tuple[str, ...] | list[str],
    *,
    genre_mix: dict[str, float] | None = None,
    genre_boost_table: dict[str, dict[str, float]] | None = None,
    composition_archetype: str | None = None,
    mood: str = "",
    energy_level: int = 3,
    field: str = "pattern",
    recent: list[str] | None = None,
):
    """Como weighted_pick, con registro auditable (PatternFieldAudit)."""
    from cadence.music.pattern_selection_audit import build_selection_reason
    from cadence.schemas.song_state import PatternFieldAudit

    chosen, expanded, weights, jitter, target_ratio = _weighted_pick_core(
        seed, salt, candidates, pool,
        genre_mix=genre_mix,
        genre_boost_table=genre_boost_table,
        composition_archetype=composition_archetype,
        mood=mood,
        energy_level=energy_level,
        field=field,
        recent=recent,
    )
    rounded = {k: round(v, 3) for k, v in weights.items()}
    return PatternFieldAudit(
        field=field,
        candidates=expanded,
        weights=rounded,
        chosen=chosen,
        selection_reason=build_selection_reason(
            chosen=chosen,
            weights=weights,
            seed=seed,
            salt=salt,
            jitter=jitter,
            target_ratio=target_ratio,
            field=field,
        ),
    )
