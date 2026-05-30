"""Afinidad patrón/capa por categoría de genre_catalog — no por tags sueltos."""

from __future__ import annotations

from cadence.music.genre_catalog import (
    category_mix_from_genre_mix,
    category_mix_from_genres,
    dominant_category,
)
from cadence.music.pattern_registry import pattern_family

# Familias preferidas por categoría (drum / bass / harmony).
DRUM_CATEGORY_BOOST: dict[str, dict[str, float]] = {
    "electronic_dance": {
        "techno": 3.0, "house": 2.5, "dnb": 2.0, "breakbeat": 1.5, "default": 1.0,
    },
    "bass_and_beats": {
        "dubstep": 3.0, "breakbeat": 2.5, "halftime": 2.0, "industrial": 1.5,
    },
    "synth_retro_game": {
        "breakbeat": 2.5, "techno": 2.0, "house": 1.5, "dnb": 1.5,
    },
    "ambient_downtempo": {
        "halftime": 3.0, "default": 2.5, "house": 1.5,
    },
    "industrial_dark": {
        "industrial": 3.0, "techno": 2.5, "halftime": 2.0, "dubstep": 1.5,
    },
    "orchestral_cinematic": {
        "breakbeat": 2.5, "halftime": 2.0, "industrial": 1.8, "techno": 1.0,
    },
    "game_context": {
        "breakbeat": 3.0, "industrial": 2.5, "dubstep": 2.0, "techno": 1.5,
    },
    "mood_energy": {
        "breakbeat": 2.0, "industrial": 2.0, "dubstep": 1.5, "techno": 1.5,
    },
    "rock": {"breakbeat": 2.0, "industrial": 2.0, "default": 1.5},
    "metal": {"industrial": 2.5, "breakbeat": 2.5, "dubstep": 2.0},
    "jazz_blues_funk": {"default": 2.0, "house": 1.5, "halftime": 1.5},
    "hip_hop": {"halftime": 2.5, "default": 2.0, "breakbeat": 1.5},
    "pop_world_folk": {"house": 2.0, "default": 2.0, "halftime": 1.5},
}

BASS_CATEGORY_BOOST: dict[str, dict[str, float]] = {
    "electronic_dance": {
        "driving": 2.5, "octave_pulse": 2.0, "syncopated": 2.0,
    },
    "bass_and_beats": {
        "half_time": 3.0, "syncopated": 2.5, "driving": 2.0, "sub_drop": 1.5,
    },
    "synth_retro_game": {
        "octave_pulse": 3.0, "driving": 2.5, "syncopated": 2.0, "staccato": 1.5,
    },
    "ambient_downtempo": {
        "pulse": 3.0, "half_time": 2.5, "root_fifth": 2.0,
    },
    "industrial_dark": {
        "driving": 2.5, "syncopated": 2.5, "half_time": 2.0,
    },
    "orchestral_cinematic": {
        "driving": 3.0, "octave_pulse": 2.5, "half_time": 2.0, "walk": 1.5,
    },
    "game_context": {
        "driving": 3.0, "octave_pulse": 2.5, "syncopated": 2.5,
    },
    "mood_energy": {
        "driving": 2.5, "syncopated": 2.0, "octave_pulse": 2.0,
    },
}

HARMONY_CATEGORY_BOOST: dict[str, dict[str, float]] = {
    "electronic_dance": {"dance": 2.5, "dark": 2.0, "modal": 1.5, "aggressive": 1.5},
    "bass_and_beats": {"aggressive": 3.0, "dark": 2.5, "dance": 2.0},
    "synth_retro_game": {"dance": 3.0, "game": 2.5, "aggressive": 1.5},
    "ambient_downtempo": {"modal": 2.5, "cinematic": 2.0, "dark": 1.5},
    "industrial_dark": {"dark": 3.0, "aggressive": 2.5, "modal": 1.5},
    "orchestral_cinematic": {
        "cinematic": 3.0, "aggressive": 2.5, "dark": 2.0, "game": 1.5,
    },
    "game_context": {"aggressive": 3.0, "game": 2.5, "cinematic": 2.0},
    "mood_energy": {"aggressive": 2.5, "cinematic": 2.0, "dark": 2.0},
}

OPTIONAL_LAYER_CATEGORY_WEIGHTS: dict[str, dict[str, float]] = {
    "synth_retro_game": {
        "arp_synth": 3.0, "synth_pluck": 2.5, "echo_synth": 2.0,
    },
    "electronic_dance": {
        "chord_stab": 2.5, "perc_aux": 2.0, "arp_synth": 1.5,
    },
    "bass_and_beats": {
        "chord_stab": 3.0, "perc_aux": 2.5, "echo_synth": 2.0,
    },
    "orchestral_cinematic": {
        "pad": 3.0, "countermelody": 2.5, "chord_stab": 2.0,
    },
    "ambient_downtempo": {
        "pad": 3.0, "echo_synth": 2.5,
    },
    "game_context": {
        "countermelody": 3.0, "chord_stab": 2.5, "perc_aux": 2.5, "arp_synth": 2.0,
    },
}

# Sesgo de ladder rítmica por categoría dominante (clave rhythm_fallback_ladders).
CATEGORY_RHYTHM_LADDER_BIAS: dict[str, str] = {
    "bass_and_beats": "dance",
    "synth_retro_game": "dance",
    "electronic_dance": "game_high",
    "orchestral_cinematic": "boss",
    "game_context": "boss",
    "ambient_downtempo": "loop",
    "industrial_dark": "game_high",
}

ARP_CATEGORY_BOOST: dict[str, dict[str, float]] = {
    "synth_retro_game": {"sixteenth": 3.0, "cascade": 2.5, "syncopated": 2.0},
    "electronic_dance": {"sixteenth": 2.5, "syncopated": 2.0, "broken": 1.5},
    "orchestral_cinematic": {"broken": 2.5, "up": 2.0, "pingpong": 1.5},
    "bass_and_beats": {"syncopated": 2.5, "broken": 2.0},
}

STAB_CATEGORY_BOOST: dict[str, dict[str, float]] = {
    "orchestral_cinematic": {"orchestral_sync": 3.0, "half_bar": 2.0},
    "electronic_dance": {"four_on": 2.5, "sixteenth": 2.0},
    "bass_and_beats": {"syncopated": 2.5, "offbeat": 2.0},
    "game_context": {"orchestral_sync": 2.5, "sixteenth": 2.0},
}

_FIELD_CATEGORY_TABLES: dict[str, dict[str, dict[str, float]]] = {
    "drum": DRUM_CATEGORY_BOOST,
    "bass": BASS_CATEGORY_BOOST,
    "harmony": HARMONY_CATEGORY_BOOST,
    "arp": ARP_CATEGORY_BOOST,
    "stab": STAB_CATEGORY_BOOST,
    "perc": STAB_CATEGORY_BOOST,
    "pluck": ARP_CATEGORY_BOOST,
    "counter": STAB_CATEGORY_BOOST,
    "pattern": {},
}


def apply_category_boosts(
    weights: dict[str, float],
    candidates: list[str],
    field: str,
    category_mix: dict[str, float],
    *,
    multiplier: float = 2.2,
) -> None:
    """Suma boosts por categoría del catálogo (familias de patrón)."""
    table = _FIELD_CATEGORY_TABLES.get(field)
    if not table or not category_mix:
        return
    for category, cat_weight in category_mix.items():
        if cat_weight <= 0:
            continue
        boosts = table.get(category, {})
        for pid in candidates:
            fam = pattern_family(pid)
            for key, boost in boosts.items():
                if key == pid or key == fam:
                    weights[pid] = weights.get(pid, 0.0) + cat_weight * boost * multiplier


def category_score_optional_layer(
    instrument_id: str,
    category_mix: dict[str, float],
) -> float:
    score = 0.0
    for category, cat_weight in category_mix.items():
        layer_w = OPTIONAL_LAYER_CATEGORY_WEIGHTS.get(category, {}).get(instrument_id, 0)
        score += cat_weight * layer_w
    return score


def rhythm_ladder_bias_from_categories(
    category_mix: dict[str, float],
    *,
    energy_level: int = 3,
) -> str | None:
    """Clave de ladder sugerida por categoría dominante."""
    dom = dominant_category(category_mix)
    if dom and dom in CATEGORY_RHYTHM_LADDER_BIAS:
        bias = CATEGORY_RHYTHM_LADDER_BIAS[dom]
        if dom == "electronic_dance" and energy_level <= 3:
            return "game_mid"
        return bias
    return None


__all__ = [
    "apply_category_boosts",
    "category_mix_from_genre_mix",
    "category_mix_from_genres",
    "category_score_optional_layer",
    "dominant_category",
    "rhythm_ladder_bias_from_categories",
    "DRUM_CATEGORY_BOOST",
    "BASS_CATEGORY_BOOST",
    "HARMONY_CATEGORY_BOOST",
]
