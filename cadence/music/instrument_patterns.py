"""Patrones rítmicos reutilizables para capas deterministas."""

from __future__ import annotations

# ── Stabs (pasos 16th por compás) ─────────────────────────────

_STAB_BASE: dict[str, tuple[int, ...]] = {
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

_STAB_B: dict[str, tuple[int, ...]] = {
    "offbeat": (9, 13),
    "four_on": (2, 6, 10, 14),
    "syncopated": (3, 7, 11, 15),
    "half_bar": (4, 12),
    "sparse": (14,),
    "dubstep_off": (11, 15),
    "sixteenth": tuple(i for i in range(16) if i % 2 == 0),
    "organ_offbeat": (1, 3, 5, 7, 9, 11, 13, 15),
    "orchestral_sync": (1, 4, 7, 9, 12, 15),
}


def _build_step_catalog(
    base: dict[str, tuple[int, ...]],
    overrides_b: dict[str, tuple[int, ...]],
) -> tuple[dict[str, tuple[int, ...]], tuple[str, ...], dict[str, str]]:
    patterns: dict[str, tuple[int, ...]] = {}
    pool: list[str] = []
    aliases: dict[str, str] = {}
    for family, steps_a in base.items():
        cid_a = f"{family}_a"
        patterns[cid_a] = steps_a
        pool.append(cid_a)
        aliases[family] = cid_a
        cid_b = f"{family}_b"
        patterns[cid_b] = overrides_b.get(family, steps_a)
        pool.append(cid_b)
    return patterns, tuple(pool), aliases


STAB_STEP_PATTERNS, STAB_PATTERN_POOL, STAB_PATTERN_ALIASES = _build_step_catalog(
    _STAB_BASE, _STAB_B,
)

# ── Perc aux ──────────────────────────────────────────────────

_PERC_BASE: dict[str, tuple[int, ...]] = {
    "backbeat": (4, 12),
    "four_clap": (0, 4, 8, 12),
    "syncopated": (2, 6, 10, 14),
    "sparse": (12,),
    "shuffle": (3, 7, 11, 15),
}

_PERC_B: dict[str, tuple[int, ...]] = {
    "backbeat": (5, 13),
    "four_clap": (2, 6, 10, 14),
    "syncopated": (1, 5, 9, 13),
    "sparse": (15,),
    "shuffle": (1, 4, 7, 10, 13),
}

PERC_CLAP_PATTERNS, PERC_PATTERN_POOL, PERC_PATTERN_ALIASES = _build_step_catalog(
    _PERC_BASE, _PERC_B,
)

# ── Synth pluck (una nota por golpe) ──────────────────────────

_PLUCK_BASE: dict[str, tuple[int, ...]] = {
    "eighth": (0, 4, 8, 12),
    "sixteenth": (0, 2, 4, 6, 8, 10, 12, 14),
    "syncopated": (0, 3, 8, 11),
    "sparse": (0, 8),
    "triplet_feel": (0, 2, 4, 8, 10, 12),
}

_PLUCK_B: dict[str, tuple[int, ...]] = {
    "eighth": (2, 6, 10, 14),
    "sixteenth": (1, 3, 5, 7, 9, 11, 13, 15),
    "syncopated": (2, 5, 9, 13),
    "sparse": (4, 12),
    "triplet_feel": (1, 3, 5, 9, 11, 13),
}

PLUCK_STEP_PATTERNS, PLUCK_PATTERN_POOL, PLUCK_PATTERN_ALIASES = _build_step_catalog(
    _PLUCK_BASE, _PLUCK_B,
)

# ── Countermelody (pasos 16th) ─────────────────────────────────

_COUNTER_BASE: dict[str, tuple[int, ...]] = {
    "offbeat_sync": (4, 6, 12, 14),
    "backbeat": (4, 12),
    "syncopated": (2, 6, 10, 14),
    "sparse": (6, 14),
    "sixteenth": (0, 2, 4, 6, 8, 10, 12, 14),
    "orchestral_sync": (0, 3, 6, 8, 11, 14),
    "call_response": (2, 10, 14),
}

_COUNTER_B: dict[str, tuple[int, ...]] = {
    "offbeat_sync": (5, 7, 13, 15),
    "backbeat": (5, 13),
    "syncopated": (1, 5, 9, 13),
    "sparse": (7, 15),
    "sixteenth": (1, 3, 5, 7, 9, 11, 13, 15),
    "orchestral_sync": (1, 4, 7, 9, 12, 15),
    "call_response": (3, 11, 15),
}

COUNTER_STEP_PATTERNS, COUNTER_PATTERN_POOL, COUNTER_PATTERN_ALIASES = _build_step_catalog(
    _COUNTER_BASE, _COUNTER_B,
)


def _resolve_step_pattern(
    pattern_id: str | None,
    patterns: dict[str, tuple[int, ...]],
    aliases: dict[str, str],
    pool: tuple[str, ...],
    generation_seed: int,
    salt: int,
    default: str,
) -> tuple[int, ...]:
    from cadence.music.pattern_registry import resolve_pattern_id
    from cadence.music.pattern_selection import weighted_pick

    if pattern_id:
        rid = resolve_pattern_id(pattern_id, aliases, default=default)
        if rid in patterns:
            return patterns[rid]
    pid = weighted_pick(
        generation_seed, salt, list(pool), pool, field="layer",
    )
    return patterns[pid]


def stab_steps(pattern_id: str | None, generation_seed: int = 0) -> tuple[int, ...]:
    return _resolve_step_pattern(
        pattern_id, STAB_STEP_PATTERNS, STAB_PATTERN_ALIASES,
        STAB_PATTERN_POOL, generation_seed, 23, "offbeat_a",
    )


def perc_clap_steps(pattern_id: str | None, generation_seed: int = 0) -> tuple[int, ...]:
    return _resolve_step_pattern(
        pattern_id, PERC_CLAP_PATTERNS, PERC_PATTERN_ALIASES,
        PERC_PATTERN_POOL, generation_seed, 31, "backbeat_a",
    )


def pluck_steps(pattern_id: str | None, generation_seed: int = 0) -> tuple[int, ...]:
    return _resolve_step_pattern(
        pattern_id, PLUCK_STEP_PATTERNS, PLUCK_PATTERN_ALIASES,
        PLUCK_PATTERN_POOL, generation_seed, 41, "eighth_a",
    )


def counter_steps(pattern_id: str | None, generation_seed: int = 0) -> tuple[int, ...]:
    return _resolve_step_pattern(
        pattern_id, COUNTER_STEP_PATTERNS, COUNTER_PATTERN_ALIASES,
        COUNTER_PATTERN_POOL, generation_seed, 37, "offbeat_sync_a",
    )


def perc_use_shaker(pattern_id: str | None, density: float) -> bool:
    from cadence.music.pattern_registry import pattern_family

    fam = pattern_family(pattern_id or "")
    if fam in ("four_clap", "syncopated", "shuffle"):
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
    "call_response": "Dos golpes de pregunta/respuesta — diálogo melódico.",
}

PERC_PATTERN_INFO: dict[str, str] = {
    "backbeat": "Claps en 2 y 4 — clásico dance.",
    "four_clap": "Clap en cada negra + shaker si hay densidad.",
    "syncopated": "Claps syncopados + shaker.",
    "sparse": "Un clap por compás — ligero.",
    "shuffle": "Claps en shuffle (3,7,11,15) — groove desplazado.",
}

PLUCK_PATTERN_INFO: dict[str, str] = {
    "eighth": "Raíz del acorde en negras — groove estable.",
    "sixteenth": "Plucks en semicorcheas — alta energía.",
    "syncopated": "Plucks desplazados — tensión rítmica.",
    "sparse": "Dos plucks por compás — respiración.",
    "triplet_feel": "Plucks en feel ternario — textura ágil.",
}


def format_layer_patterns_for_llm() -> str:
    """Catálogo de patrones de capas opcionales para instrument_planner."""
    lines = ["Patrones de capas (opcional — vacío = default por seed):"]
    from cadence.music.pattern_registry import pattern_family

    lines.append("\nchord_stab — stab_pattern:")
    for pid in STAB_PATTERN_POOL:
        fam = pattern_family(pid)
        info = STAB_PATTERN_INFO.get(fam, STAB_PATTERN_INFO.get(pid, pid))
        lines.append(f"  • {pid}: {info}")
    lines.append("\nperc_aux — perc_pattern:")
    for pid in PERC_PATTERN_POOL:
        fam = pattern_family(pid)
        info = PERC_PATTERN_INFO.get(fam, PERC_PATTERN_INFO.get(pid, pid))
        lines.append(f"  • {pid}: {info}")
    lines.append("\nsynth_pluck — pluck_pattern (solo si activas synth_pluck):")
    for pid in PLUCK_PATTERN_POOL:
        fam = pattern_family(pid)
        info = PLUCK_PATTERN_INFO.get(fam, PLUCK_PATTERN_INFO.get(pid, pid))
        lines.append(f"  • {pid}: {info}")
    lines.append("\ncountermelody — counter_pattern:")
    for pid in COUNTER_PATTERN_POOL:
        fam = pattern_family(pid)
        info = COUNTER_PATTERN_INFO.get(fam, COUNTER_PATTERN_INFO.get(pid, pid))
        lines.append(f"  • {pid}: {info}")
    lines.append(
        "\nSi activas chord_stab, perc_aux, synth_pluck o countermelody, elige un patrón "
        "coherente con drum/bass y el género."
    )
    return "\n".join(lines)
