"""Patrones rítmicos reutilizables para capas deterministas."""

from __future__ import annotations

# ── Stabs (pasos 16th por compás) ─────────────────────────────

STAB_STEP_PATTERNS: dict[str, tuple[int, ...]] = {
    "offbeat": (8, 12),
    "four_on": (0, 4, 8, 12),
    "syncopated": (2, 6, 10, 14),
    "half_bar": (0, 8),
    "sparse": (12,),
    "dubstep_off": (10, 14),
    "sixteenth": tuple(range(16)),
    "organ_offbeat": (0, 2, 4, 6, 8, 10, 12, 14),
    "orchestral_sync": (0, 3, 6, 8, 11, 14),
}

STAB_PATTERN_POOL = tuple(STAB_STEP_PATTERNS.keys())

# ── Perc aux ──────────────────────────────────────────────────

PERC_CLAP_PATTERNS: dict[str, tuple[int, ...]] = {
    "backbeat": (4, 12),
    "four_clap": (0, 4, 8, 12),
    "syncopated": (2, 6, 10, 14),
    "sparse": (12,),
}

PERC_PATTERN_POOL = tuple(PERC_CLAP_PATTERNS.keys())

# ── Synth pluck (una nota por golpe) ──────────────────────────

PLUCK_STEP_PATTERNS: dict[str, tuple[int, ...]] = {
    "eighth": (0, 4, 8, 12),
    "sixteenth": (0, 2, 4, 6, 8, 10, 12, 14),
    "syncopated": (0, 3, 8, 11),
    "sparse": (0, 8),
}

PLUCK_PATTERN_POOL = tuple(PLUCK_STEP_PATTERNS.keys())

# ── Countermelody (pasos 16th) ─────────────────────────────────

COUNTER_STEP_PATTERNS: dict[str, tuple[int, ...]] = {
    "offbeat_sync": (4, 6, 12, 14),
    "backbeat": (4, 12),
    "syncopated": (2, 6, 10, 14),
    "sparse": (6, 14),
    "sixteenth": (0, 2, 4, 6, 8, 10, 12, 14),
    "orchestral_sync": (0, 3, 6, 8, 11, 14),
}

COUNTER_PATTERN_POOL = tuple(COUNTER_STEP_PATTERNS.keys())


def _pick(pool: tuple[str, ...], seed: int, salt: int) -> str:
    return pool[(seed // salt) % len(pool)]


def stab_steps(pattern_id: str | None, generation_seed: int = 0) -> tuple[int, ...]:
    if pattern_id and pattern_id in STAB_STEP_PATTERNS:
        return STAB_STEP_PATTERNS[pattern_id]
    pid = _pick(STAB_PATTERN_POOL, generation_seed, 23)
    return STAB_STEP_PATTERNS[pid]


def perc_clap_steps(pattern_id: str | None, generation_seed: int = 0) -> tuple[int, ...]:
    if pattern_id and pattern_id in PERC_CLAP_PATTERNS:
        return PERC_CLAP_PATTERNS[pattern_id]
    pid = _pick(PERC_PATTERN_POOL, generation_seed, 31)
    return PERC_CLAP_PATTERNS[pid]


def pluck_steps(pattern_id: str | None, generation_seed: int = 0) -> tuple[int, ...]:
    if pattern_id and pattern_id in PLUCK_STEP_PATTERNS:
        return PLUCK_STEP_PATTERNS[pattern_id]
    pid = _pick(PLUCK_PATTERN_POOL, generation_seed, 41)
    return PLUCK_STEP_PATTERNS[pid]


def counter_steps(pattern_id: str | None, generation_seed: int = 0) -> tuple[int, ...]:
    if pattern_id and pattern_id in COUNTER_STEP_PATTERNS:
        return COUNTER_STEP_PATTERNS[pattern_id]
    pid = _pick(COUNTER_PATTERN_POOL, generation_seed, 37)
    return COUNTER_STEP_PATTERNS[pid]


def perc_use_shaker(pattern_id: str | None, density: float) -> bool:
    if pattern_id in ("four_clap", "syncopated"):
        return True
    return density >= 0.7


STAB_PATTERN_INFO: dict[str, str] = {
    "offbeat": "Stabs en beats 2 y 4 — deja espacio a la melodía.",
    "four_on": "Stab en cada negra — densidad armónica constante.",
    "syncopated": "Stabs desplazados — groove inquieto.",
    "half_bar": "Dos golpes por compás — medio denso.",
    "sparse": "Un stab al final del compás — mínimo.",
    "dubstep_off": "Offbeats tardíos (10, 14) — estilo dubstep/brostep.",
    "sixteenth": "Stab en cada semicorchea — hiper-denso dance/battle.",
    "organ_offbeat": "Ocho golpes alternados (0–14) — estilo organ/hyperpop.",
    "orchestral_sync": "Sincopa orquestal (0,3,6,8,11,14) — capas cinemáticas.",
}

COUNTER_PATTERN_INFO: dict[str, str] = {
    "offbeat_sync": "Contramelodía en 4,6,12,14 — clásico boss energético.",
    "backbeat": "Dos entradas en 2 y 4 — respuesta simple.",
    "syncopated": "Cuatro golpes desplazados — tensión rítmica.",
    "sparse": "Dos notas por compás — aire en el registro alto.",
    "sixteenth": "Ocho entradas por compás — contramelodía densa.",
    "orchestral_sync": "Grid orquestal — textura épica sin saturar.",
}

PERC_PATTERN_INFO: dict[str, str] = {
    "backbeat": "Claps en 2 y 4 — clásico dance.",
    "four_clap": "Clap en cada negra + shaker si hay densidad.",
    "syncopated": "Claps syncopados + shaker.",
    "sparse": "Un clap por compás — ligero.",
}

PLUCK_PATTERN_INFO: dict[str, str] = {
    "eighth": "Raíz del acorde en negras — groove estable.",
    "sixteenth": "Plucks en semicorcheas — alta energía.",
    "syncopated": "Plucks desplazados — tensión rítmica.",
    "sparse": "Dos plucks por compás — respiración.",
}


def format_layer_patterns_for_llm() -> str:
    """Catálogo de patrones de capas opcionales para instrument_planner."""
    lines = ["Patrones de capas (opcional — vacío = default por seed):"]
    lines.append("\nchord_stab — stab_pattern:")
    for pid in STAB_PATTERN_POOL:
        lines.append(f"  • {pid}: {STAB_PATTERN_INFO[pid]}")
    lines.append("\nperc_aux — perc_pattern:")
    for pid in PERC_PATTERN_POOL:
        lines.append(f"  • {pid}: {PERC_PATTERN_INFO[pid]}")
    lines.append("\nsynth_pluck — pluck_pattern (solo si activas synth_pluck):")
    for pid in PLUCK_PATTERN_POOL:
        lines.append(f"  • {pid}: {PLUCK_PATTERN_INFO[pid]}")
    lines.append("\ncountermelody — counter_pattern:")
    for pid in COUNTER_PATTERN_POOL:
        lines.append(f"  • {pid}: {COUNTER_PATTERN_INFO[pid]}")
    lines.append(
        "\nSi activas chord_stab, perc_aux, synth_pluck o countermelody, elige un patrón "
        "coherente con drum/bass y el género."
    )
    return "\n".join(lines)
