"""Afinidad género → candidatos de patrón (drums/bass/harmony/capas)."""

from __future__ import annotations

from cadence.music.arp_patterns import ARP_PATTERNS
from cadence.music.pattern_registry import pattern_family
from cadence.music.instrument_patterns import (
    COUNTER_PATTERN_POOL,
    PERC_PATTERN_POOL,
    PLUCK_PATTERN_POOL,
    STAB_PATTERN_POOL,
)
# Boost por género canónico (0 = neutro). Varios géneros compiten sin anular el arquetipo.
DRUM_GENRE_BOOST: dict[str, dict[str, float]] = {
    "techno": {"techno": 3.0, "industrial": 2.0, "house": 1.5},
    "industrial": {"industrial": 3.0, "techno": 2.0, "dubstep": 1.0},
    "house": {"house": 3.0, "techno": 1.5, "default": 1.0},
    "dubstep": {"dubstep": 3.0, "breakbeat": 2.0, "halftime": 1.5},
    "breakbeat": {"breakbeat": 3.0, "dnb": 2.0, "techno": 1.0},
    "drum and bass": {"dnb": 3.0, "breakbeat": 2.0},
    "dnb": {"dnb": 3.0, "breakbeat": 2.0},
    "chiptune": {"breakbeat": 2.0, "techno": 1.5, "house": 1.0},
    "arcade": {"breakbeat": 2.5, "techno": 1.5},
    "eurobeat": {"techno": 2.0, "house": 2.0, "breakbeat": 1.5},
    "orchestral": {"breakbeat": 2.0, "industrial": 1.5, "halftime": 1.5, "techno": 1.0},
    "symphonic": {"breakbeat": 2.0, "industrial": 1.5, "halftime": 1.5},
    "cinematic": {"halftime": 2.0, "breakbeat": 1.5, "industrial": 1.0},
    "epic": {"breakbeat": 2.5, "industrial": 2.0, "dubstep": 1.0},
    "hybrid orchestral": {"breakbeat": 2.5, "industrial": 2.0, "dubstep": 1.5},
    "boss fight": {"breakbeat": 3.0, "industrial": 2.5, "dubstep": 2.0, "techno": 1.0},
    "battle": {"breakbeat": 2.5, "industrial": 2.0, "dubstep": 1.5},
    "aggressive": {"industrial": 2.5, "dubstep": 2.0, "breakbeat": 2.0},
    "dark": {"industrial": 2.0, "halftime": 1.5, "dubstep": 1.0},
}

BASS_GENRE_BOOST: dict[str, dict[str, float]] = {
    "techno": {"driving": 2.5, "octave_pulse": 2.0, "syncopated": 1.5},
    "dubstep": {"half_time": 3.0, "syncopated": 2.0, "driving": 1.5},
    "house": {"driving": 2.0, "root_fifth": 1.5, "pulse": 1.0},
    "orchestral": {"driving": 2.5, "octave_pulse": 2.0, "half_time": 1.5},
    "cinematic": {"half_time": 2.0, "driving": 2.0, "pulse": 1.0},
    "boss fight": {"driving": 3.0, "octave_pulse": 2.5, "syncopated": 2.0},
    "chiptune": {"octave_pulse": 3.0, "driving": 2.0, "syncopated": 1.5},
    "industrial": {"driving": 2.5, "octave_pulse": 2.0, "syncopated": 2.0},
}

HARMONY_GENRE_BOOST: dict[str, dict[str, float]] = {
    "techno": {"dark": 2.0, "modal": 1.5, "aggressive": 1.5, "dance": 1.0},
    "dubstep": {"aggressive": 2.5, "dark": 2.0, "dance": 1.5},
    "orchestral": {"cinematic": 3.0, "dark": 2.0, "aggressive": 2.0, "game": 1.0},
    "cinematic": {"cinematic": 3.0, "dark": 2.0, "modal": 1.5},
    "epic": {"cinematic": 2.5, "aggressive": 2.5, "dark": 1.5},
    "boss fight": {"aggressive": 3.0, "cinematic": 2.5, "dark": 2.0, "game": 1.5},
    "chiptune": {"dance": 2.5, "game": 2.0, "aggressive": 1.5},
    "house": {"dance": 2.5, "game": 1.5, "modal": 1.0},
}

ARP_GENRE_BOOST: dict[str, dict[str, float]] = {
    "techno": {"sixteenth": 2.0, "syncopated": 1.5, "broken": 1.0},
    "chiptune": {"sixteenth": 3.0, "cascade": 2.0, "syncopated": 1.5},
    "orchestral": {"broken": 2.5, "up": 2.0, "pingpong": 1.5},
    "boss fight": {"broken": 2.0, "syncopated": 2.0, "sixteenth": 1.5},
    "dubstep": {"syncopated": 2.0, "broken": 1.5},
}

STAB_GENRE_BOOST: dict[str, dict[str, float]] = {
    "orchestral": {"orchestral_sync": 3.0, "half_bar": 2.0, "offbeat": 1.0},
    "cinematic": {"orchestral_sync": 2.5, "half_bar": 2.0},
    "techno": {"four_on": 2.0, "sixteenth": 1.5, "syncopated": 1.5},
    "boss fight": {"orchestral_sync": 2.5, "sixteenth": 2.0, "four_on": 1.5},
    "dubstep": {"syncopated": 2.5, "offbeat": 2.0},
}

PERC_GENRE_BOOST: dict[str, dict[str, float]] = {
    "techno": {"four_clap": 2.0, "syncopated": 1.5},
    "boss fight": {"syncopated": 2.5, "four_clap": 2.0, "backbeat": 1.5},
    "orchestral": {"syncopated": 2.0, "four_clap": 1.5},
}

COUNTER_GENRE_BOOST: dict[str, dict[str, float]] = {
    "orchestral": {"orchestral_sync": 3.0, "offbeat_sync": 2.0},
    "boss fight": {"orchestral_sync": 2.5, "offbeat_sync": 2.0, "sixteenth": 1.5},
    "techno": {"offbeat_sync": 2.0, "sixteenth": 1.5},
}

PLUCK_GENRE_BOOST: dict[str, dict[str, float]] = {
    "chiptune": {"sixteenth": 3.0, "eighth": 2.0},
    "techno": {"eighth": 2.0, "syncopated": 1.5},
    "orchestral": {"sparse": 2.0, "eighth": 1.5},
}


def _score_candidates(
    base_order: list[str],
    pool: tuple[str, ...] | list[str],
    genre_mix: dict[str, float],
    boost_table: dict[str, dict[str, float]],
    *,
    rank_offset: float = 10.0,
    field: str = "drum",
) -> list[str]:
    """Reordena candidatos: prioridad base + boosts ponderados por genre_mix."""
    pool_set = set(pool)
    scores: dict[str, float] = {}
    for rank, pid in enumerate(base_order):
        fam = pattern_family(pid)
        for pool_pid in pool_set:
            if pool_pid == pid or pattern_family(pool_pid) == fam:
                scores[pool_pid] = max(scores.get(pool_pid, 0.0), rank_offset - rank)

    for genre, weight in genre_mix.items():
        if weight <= 0:
            continue
        boosts = boost_table.get(genre, {})
        for pool_pid in pool_set:
            fam = pattern_family(pool_pid)
            for key, boost in boosts.items():
                if key == pool_pid or key == fam:
                    scores[pool_pid] = scores.get(pool_pid, 0.0) + weight * boost

    from cadence.music.genre_catalog import category_mix_from_genre_mix
    from cadence.music.genre_category_patterns import apply_category_boosts

    cat_mix = category_mix_from_genre_mix(genre_mix)
    if cat_mix:
        cat_weights = {pid: scores.get(pid, 0.0) for pid in pool_set}
        apply_category_boosts(cat_weights, list(pool_set), field, cat_mix)
        for pid, w in cat_weights.items():
            scores[pid] = max(scores.get(pid, 0.0), w)

    for pid in pool:
        scores.setdefault(pid, 0.0)

    return sorted(scores.keys(), key=lambda p: (-scores[p], p))


def rank_drum_candidates(
    base: list[str], genre_mix: dict[str, float],
) -> list[str]:
    from cadence.music.strategy_pools import DRUM_POOL

    return _score_candidates(base, DRUM_POOL, genre_mix, DRUM_GENRE_BOOST, field="drum")


def rank_bass_candidates(
    base: list[str], genre_mix: dict[str, float],
) -> list[str]:
    from cadence.music.strategy_pools import BASS_POOL

    return _score_candidates(base, BASS_POOL, genre_mix, BASS_GENRE_BOOST, field="bass")


def rank_harmony_candidates(
    base: list[str], genre_mix: dict[str, float],
) -> list[str]:
    from cadence.music.strategy_pools import HARMONY_POOL

    return _score_candidates(base, HARMONY_POOL, genre_mix, HARMONY_GENRE_BOOST, field="harmony")


def rank_layer_candidates(
    base: list[str] | None,
    pool: tuple[str, ...],
    genre_mix: dict[str, float],
    boost_table: dict[str, dict[str, float]],
    *,
    field: str = "pattern",
) -> list[str]:
    if not base:
        base = list(pool)
    return _score_candidates(base, pool, genre_mix, boost_table, field=field)


def layer_bias_from_genre_mix(
    base_bias: dict[str, list[str] | str],
    genre_mix: dict[str, float],
) -> dict[str, list[str] | str]:
    """Enriquece layer_pattern_bias con ranking por género compuesto."""
    bias = dict(base_bias)
    mapping = [
        ("arp_candidates", ARP_PATTERNS, ARP_GENRE_BOOST, "arp"),
        ("stab_candidates", STAB_PATTERN_POOL, STAB_GENRE_BOOST, "stab"),
        ("perc_candidates", PERC_PATTERN_POOL, PERC_GENRE_BOOST, "perc"),
        ("pluck_candidates", PLUCK_PATTERN_POOL, PLUCK_GENRE_BOOST, "pluck"),
        ("counter_candidates", COUNTER_PATTERN_POOL, COUNTER_GENRE_BOOST, "counter"),
    ]
    for key, pool, table, fld in mapping:
        raw = bias.get(key)
        if isinstance(raw, list):
            bias[key] = rank_layer_candidates(raw, pool, genre_mix, table, field=fld)
        elif raw is None and genre_mix:
            bias[key] = rank_layer_candidates(list(pool), pool, genre_mix, table, field=fld)
    if "bass_candidates" in bias and isinstance(bias["bass_candidates"], list):
        bias["bass_candidates"] = rank_bass_candidates(bias["bass_candidates"], genre_mix)
    return bias
