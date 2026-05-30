"""Pools de estrategias compositivas — selección determinista por generation_seed."""

from cadence.schemas.song_state import GenerationStrategies
from cadence.music.arp_patterns import ARP_PATTERNS
from cadence.music.instrument_patterns import (
    COUNTER_PATTERN_POOL,
    PERC_PATTERN_POOL,
    PLUCK_PATTERN_POOL,
    STAB_PATTERN_POOL,
)
from cadence.music.repertoire_signals import (
    bass_pool_priority,
    drum_pool_priority,
    harmony_pool_priority,
    layer_pattern_bias,
)

# ── Patrones de batería (16 steps, 4/4) ───────────────────────

DRUM_PATTERNS: dict[str, dict[str, list[int]]] = {
    "techno": {
        "kick":  [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "hihat": [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    },
    "dubstep": {
        "kick":  [1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0],
        "hihat": [1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1],
    },
    "house": {
        "kick":  [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "hihat": [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0],
    },
    "breakbeat": {
        "kick":  [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0],
        "hihat": [1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0],
    },
    "halftime": {
        "kick":  [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "hihat": [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
    },
    "dnb": {
        "kick":  [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1],
        "hihat": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    },
    "industrial": {
        "kick":  [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "hihat": [1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1],
    },
    "default": {
        "kick":  [1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "hihat": [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    },
}

DRUM_POOL = [
    "techno", "dubstep", "house", "breakbeat",
    "halftime", "dnb", "industrial", "default",
]

DRUM_PATTERN_INFO: dict[str, str] = {
    "techno": "Kick four-on-the-floor, snare en 2 y 4, hi-hat en corcheas — industrial/techno oscuro.",
    "dubstep": "Kick syncopado con doble snare, hi-hat denso — brostep/agresivo.",
    "house": "Kick four-on-the-floor, snare clásico, hi-hat en off-beats — groove estable.",
    "breakbeat": "Kick y snare desplazados estilo break — tensión rítmica, boss fights.",
    "halftime": "Half-time: kick y snare espaciados — drops dubstep/trap.",
    "dnb": "Kick doble y hats continuos — drum and bass / neuro.",
    "industrial": "Kick y hats densos, snare seco — techno industrial / EBM.",
    "default": "Patrón equilibrado genérico — neutro si ningún estilo encaja.",
}

# ── Patrones de bajo (step, root|fifth) ───────────────────────

BassStep = tuple[int, str]

BASS_PATTERNS: dict[str, list[BassStep]] = {
    "root_fifth": [(0, "root"), (4, "root"), (8, "fifth"), (12, "root")],
    "driving": [(0, "root"), (3, "root"), (8, "fifth"), (11, "fifth")],
    "syncopated": [(2, "root"), (6, "fifth"), (10, "root"), (14, "fifth")],
    "pulse": [(0, "root"), (8, "root")],
    "half_time": [(0, "root"), (8, "root"), (12, "fifth")],
    "walk": [(0, "root"), (2, "root"), (4, "fifth"), (6, "root"), (8, "fifth"), (10, "root"), (12, "root"), (14, "fifth")],
    "octave_pulse": [(0, "root"), (4, "root"), (8, "root"), (12, "root")],
}

BASS_POOL = list(BASS_PATTERNS.keys())

BASS_PATTERN_INFO: dict[str, str] = {
    "root_fifth": "Raíz y quinta en compás — clásico, legible en juego.",
    "driving": "Raíz repetida con quintas en off-beats — impulso constante.",
    "syncopated": "Entradas desplazadas — groove más inquieto/tensión.",
    "pulse": "Solo raíz en 1 y 3 — mínimo, loops y cutscenes.",
    "half_time": "Raíz en 1 y 3 con quinta — half-time dubstep/trap.",
    "walk": "Caminata cromática en semicorcheas — jazz/funk game.",
    "octave_pulse": "Raíz en cada negra — sub presión constante.",
}

# ── Pools de progresiones armónicas ───────────────────────────

PROGRESSIONS_CLASSIC_MINOR = {
    "default": [(0, "minor"), (5, "major"), (2, "major"), (6, "major")],
    "tension": [(0, "minor"), (3, "minor"), (5, "major"), (4, "dominant")],
    "climax": [(0, "minor"), (0, "minor"), (6, "major"), (5, "major")],
    "sparse": [(0, "minor")],
    "release": [(0, "minor"), (5, "major"), (3, "minor"), (0, "minor")],
}

PROGRESSIONS_MODAL_MINOR = {
    "default": [(0, "minor"), (3, "minor"), (5, "major"), (0, "minor")],
    "tension": [(0, "minor"), (5, "major"), (6, "major"), (4, "dominant")],
    "climax": [(0, "minor"), (6, "major"), (5, "major"), (0, "minor")],
    "sparse": [(0, "minor"), (5, "major")],
    "release": [(0, "minor"), (5, "major"), (0, "minor")],
}

PROGRESSIONS_GAME_MINOR = {
    "default": [(0, "minor"), (6, "major"), (3, "minor"), (5, "major")],
    "tension": [(0, "minor"), (4, "dominant"), (5, "major"), (6, "major")],
    "climax": [(0, "minor"), (5, "major"), (4, "dominant"), (0, "minor")],
    "sparse": [(0, "minor")],
    "release": [(0, "minor"), (3, "minor"), (5, "major"), (0, "minor")],
}

PROGRESSIONS_CLASSIC_MAJOR = {
    "default": [(0, "major"), (4, "major"), (5, "minor"), (3, "major")],
    "tension": [(0, "major"), (5, "minor"), (3, "minor"), (4, "major")],
    "climax": [(0, "major"), (0, "major"), (5, "major"), (4, "major")],
    "sparse": [(0, "major")],
    "release": [(0, "major"), (4, "major"), (5, "minor"), (0, "major")],
}

PROGRESSIONS_MODAL_MAJOR = {
    "default": [(0, "major"), (5, "minor"), (3, "minor"), (4, "major")],
    "tension": [(0, "major"), (2, "minor"), (5, "minor"), (4, "major")],
    "climax": [(0, "major"), (5, "major"), (4, "major"), (0, "major")],
    "sparse": [(0, "major")],
    "release": [(0, "major"), (3, "major"), (0, "major")],
}

PROGRESSIONS_GAME_MAJOR = {
    "default": [(0, "major"), (5, "major"), (3, "minor"), (4, "major")],
    "tension": [(0, "major"), (6, "minor"), (4, "major"), (5, "major")],
    "climax": [(0, "major"), (4, "major"), (5, "major"), (0, "major")],
    "sparse": [(0, "major")],
    "release": [(0, "major"), (5, "minor"), (0, "major")],
}

PROGRESSIONS_DARK_MINOR = {
    "default": [(0, "minor"), (3, "minor"), (6, "major"), (5, "major")],
    "tension": [(0, "minor"), (4, "dominant"), (3, "minor"), (6, "major")],
    "climax": [(0, "minor"), (6, "major"), (4, "dominant"), (0, "minor")],
    "sparse": [(0, "minor"), (3, "minor")],
    "release": [(0, "minor"), (5, "major"), (0, "minor")],
}

PROGRESSIONS_DARK_MAJOR = {
    "default": [(0, "major"), (5, "minor"), (6, "minor"), (4, "major")],
    "tension": [(0, "major"), (4, "major"), (5, "minor"), (3, "minor")],
    "climax": [(0, "major"), (6, "minor"), (4, "major"), (0, "major")],
    "sparse": [(0, "major")],
    "release": [(0, "major"), (5, "minor"), (0, "major")],
}

PROGRESSIONS_CINEMATIC_MINOR = {
    "default": [(0, "minor"), (5, "major"), (3, "minor"), (4, "dominant")],
    "tension": [(0, "minor"), (6, "major"), (4, "dominant"), (5, "major")],
    "climax": [(0, "minor"), (5, "major"), (6, "major"), (0, "minor")],
    "sparse": [(0, "minor"), (5, "major")],
    "release": [(0, "minor"), (3, "minor"), (0, "minor")],
}

PROGRESSIONS_CINEMATIC_MAJOR = {
    "default": [(0, "major"), (4, "major"), (5, "minor"), (0, "major")],
    "tension": [(0, "major"), (2, "minor"), (5, "minor"), (4, "major")],
    "climax": [(0, "major"), (5, "major"), (4, "major"), (0, "major")],
    "sparse": [(0, "major"), (5, "major")],
    "release": [(0, "major"), (4, "major"), (0, "major")],
}

PROGRESSIONS_DANCE_MINOR = {
    "default": [(0, "minor"), (6, "major"), (5, "major"), (3, "minor")],
    "tension": [(0, "minor"), (5, "major"), (6, "major"), (4, "dominant")],
    "climax": [(0, "minor"), (6, "major"), (5, "major"), (6, "major")],
    "sparse": [(0, "minor")],
    "release": [(0, "minor"), (5, "major"), (3, "minor"), (0, "minor")],
}

PROGRESSIONS_DANCE_MAJOR = {
    "default": [(0, "major"), (5, "major"), (3, "minor"), (4, "major")],
    "tension": [(0, "major"), (4, "major"), (5, "major"), (3, "minor")],
    "climax": [(0, "major"), (5, "major"), (4, "major"), (5, "major")],
    "sparse": [(0, "major")],
    "release": [(0, "major"), (3, "minor"), (0, "major")],
}

PROGRESSIONS_AGGRESSIVE_MINOR = {
    "default": [(0, "minor"), (6, "major"), (3, "minor"), (5, "major")],
    "tension": [(0, "minor"), (4, "dominant"), (5, "major"), (6, "major")],
    "climax": [(0, "minor"), (4, "dominant"), (6, "major"), (5, "major")],
    "sparse": [(0, "minor")],
    "release": [(0, "minor"), (5, "major"), (4, "dominant"), (0, "minor")],
}

PROGRESSIONS_AGGRESSIVE_MAJOR = {
    "default": [(0, "major"), (6, "minor"), (4, "major"), (5, "major")],
    "tension": [(0, "major"), (4, "major"), (6, "minor"), (5, "major")],
    "climax": [(0, "major"), (4, "major"), (5, "major"), (4, "major")],
    "sparse": [(0, "major")],
    "release": [(0, "major"), (5, "minor"), (0, "major")],
}

HARMONY_POOLS_MINOR: dict[str, dict] = {
    "classic": PROGRESSIONS_CLASSIC_MINOR,
    "modal": PROGRESSIONS_MODAL_MINOR,
    "game": PROGRESSIONS_GAME_MINOR,
    "dark": PROGRESSIONS_DARK_MINOR,
    "cinematic": PROGRESSIONS_CINEMATIC_MINOR,
    "dance": PROGRESSIONS_DANCE_MINOR,
    "aggressive": PROGRESSIONS_AGGRESSIVE_MINOR,
}

HARMONY_POOLS_MAJOR: dict[str, dict] = {
    "classic": PROGRESSIONS_CLASSIC_MAJOR,
    "modal": PROGRESSIONS_MODAL_MAJOR,
    "game": PROGRESSIONS_GAME_MAJOR,
    "dark": PROGRESSIONS_DARK_MAJOR,
    "cinematic": PROGRESSIONS_CINEMATIC_MAJOR,
    "dance": PROGRESSIONS_DANCE_MAJOR,
    "aggressive": PROGRESSIONS_AGGRESSIVE_MAJOR,
}

HARMONY_POOL = [
    "classic", "modal", "game", "dark", "cinematic", "dance", "aggressive",
]


def compute_generation_seed(raw_prompt: str, total_bars: int) -> int:
    return abs(hash(f"{raw_prompt}:{total_bars}")) % 100_000


def format_rhythm_patterns_for_llm() -> str:
    """Catálogo drum/bass para el instrument_planner."""
    lines = ["Patrones de batería (elige EXACTAMENTE uno — obligatorio):"]
    for pid in DRUM_POOL:
        lines.append(f"  • {pid}: {DRUM_PATTERN_INFO[pid]}")
    lines.append("\nPatrones de bajo (elige EXACTAMENTE uno — obligatorio):")
    for pid in BASS_POOL:
        lines.append(f"  • {pid}: {BASS_PATTERN_INFO[pid]}")
    lines.append(
        "\nElige drum y bass coherentes con género, energía y use_case. "
        "Varía respecto a un default genérico cuando el mood lo permita."
    )
    return "\n".join(lines)


ECHO_SOURCE_POOL = ("auto", "melody", "arp_synth", "chord_stab")


def _pick_biased(candidates: list[str], pool: tuple[str, ...], seed: int, salt: int) -> str:
    for pid in candidates:
        if pid in pool:
            return pid
    return pool[(seed // salt) % len(pool)]


def select_strategies(
    generation_seed: int,
    genre_tags: list[str],
    mode: str = "minor",
    use_case: str = "game",
    energy_level: int = 3,
    *,
    composition_archetype: str | None = None,
) -> GenerationStrategies:
    """Elige una estrategia de cada pool usando generation_seed y sesgo de repertorio."""
    arch = composition_archetype
    drum_candidates = drum_pool_priority(
        energy_level, use_case, composition_archetype=arch,
    )
    drum_pattern = drum_candidates[generation_seed % len(drum_candidates)]

    layer_bias = layer_pattern_bias(
        energy_level, use_case, generation_seed, composition_archetype=arch,
    )
    bass_candidates = layer_bias.get("bass_candidates")
    if isinstance(bass_candidates, list):
        bass_pattern = _pick_biased(bass_candidates, tuple(BASS_POOL), generation_seed, 7)
    else:
        bass_pattern = BASS_POOL[(generation_seed // 7) % len(BASS_POOL)]

    harmony_candidates = harmony_pool_priority(
        energy_level, use_case, composition_archetype=arch,
    )
    harmony_pool = harmony_candidates[(generation_seed // 13) % len(harmony_candidates)]

    arp_cands = layer_bias.get("arp_candidates")
    if isinstance(arp_cands, list):
        arp_pattern = _pick_biased(arp_cands, ARP_PATTERNS, generation_seed, 17)
    else:
        arp_pattern = ARP_PATTERNS[(generation_seed // 17) % len(ARP_PATTERNS)]

    stab_cands = layer_bias.get("stab_candidates")
    if isinstance(stab_cands, list):
        stab_pattern = _pick_biased(stab_cands, STAB_PATTERN_POOL, generation_seed, 19)
    else:
        stab_pattern = STAB_PATTERN_POOL[(generation_seed // 19) % len(STAB_PATTERN_POOL)]

    perc_cands = layer_bias.get("perc_candidates")
    if isinstance(perc_cands, list):
        perc_pattern = _pick_biased(perc_cands, PERC_PATTERN_POOL, generation_seed, 23)
    else:
        perc_pattern = PERC_PATTERN_POOL[(generation_seed // 23) % len(PERC_PATTERN_POOL)]

    pluck_cands = layer_bias.get("pluck_candidates")
    if isinstance(pluck_cands, list):
        pluck_pattern = _pick_biased(pluck_cands, PLUCK_PATTERN_POOL, generation_seed, 29)
    else:
        pluck_pattern = PLUCK_PATTERN_POOL[(generation_seed // 29) % len(PLUCK_PATTERN_POOL)]

    counter_cands = layer_bias.get("counter_candidates")
    if isinstance(counter_cands, list):
        counter_pattern = _pick_biased(
            counter_cands, COUNTER_PATTERN_POOL, generation_seed, 37,
        )
    else:
        counter_pattern = COUNTER_PATTERN_POOL[
            (generation_seed // 37) % len(COUNTER_PATTERN_POOL)
        ]

    echo_source = layer_bias.get("echo_source", "auto")
    if echo_source not in ECHO_SOURCE_POOL:
        echo_source = "auto"

    return GenerationStrategies(
        generation_seed=generation_seed,
        drum_pattern=drum_pattern,
        bass_pattern=bass_pattern,
        harmony_pool=harmony_pool,
        arp_pattern=arp_pattern,
        stab_pattern=stab_pattern,
        perc_pattern=perc_pattern,
        pluck_pattern=pluck_pattern,
        counter_pattern=counter_pattern,
        echo_source=echo_source,
    )


def get_drum_pattern(pattern_id: str) -> dict[str, list[int]]:
    return DRUM_PATTERNS.get(pattern_id, DRUM_PATTERNS["default"])


def get_bass_pattern(pattern_id: str) -> list[BassStep]:
    return BASS_PATTERNS.get(pattern_id, BASS_PATTERNS["root_fifth"])


def resolve_rhythm_patterns(
    drum_pattern: str,
    bass_pattern: str,
    *,
    genre_tags: list[str],
    energy_level: int,
    use_case: str,
    generation_seed: int = 0,
) -> tuple[str, str]:
    """Valida elección del agente; fallback por género/energía si el id no es válido."""
    drum = drum_pattern if drum_pattern in DRUM_POOL else None
    bass = bass_pattern if bass_pattern in BASS_POOL else None

    if drum is None:
        candidates = drum_pool_priority(energy_level, use_case)
        drum = candidates[generation_seed % len(candidates)]

    if bass is None:
        uc = (use_case or "game").lower()
        if uc in ("loop", "cutscene") or energy_level <= 2:
            bass = "pulse"
        elif energy_level >= 4:
            bass = BASS_POOL[(generation_seed // 7) % len(BASS_POOL)]
        else:
            bass = "root_fifth"

    return drum, bass


def get_harmony_templates(mode: str, pool_id: str) -> dict:
    pools = HARMONY_POOLS_MINOR if mode == "minor" else HARMONY_POOLS_MAJOR
    return pools.get(pool_id, pools["classic"])


def resolve_harmony_pool(pool_id: str | None, generation_seed: int = 0) -> str:
    if pool_id and pool_id in HARMONY_POOL:
        return pool_id
    return HARMONY_POOL[(generation_seed // 13) % len(HARMONY_POOL)]
