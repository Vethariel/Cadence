"""Desarrollo motivico determinista — transformaciones por sección y subdivisión temporal."""

from __future__ import annotations

from cadence.schemas.song_state import (
    DevelopmentPlan,
    DevelopmentSegment,
    SectionDevelopment,
    SectionIntent,
)

ROLE_TO_TRANSFORM: dict[str, str] = {
    "establish": "introduce",
    "tension": "sequence_up",
    "release": "resolve",
    "climax": "climax",
    "reflection": "fragment",
    "transition": "expand",
    "silence": "sparse",
}

# Progresiones de transformación por rol narrativo (micro-arcos dentro de la sección)
ROLE_SEGMENT_PROGRESSIONS: dict[str, list[str]] = {
    "establish": ["introduce", "expand", "ostinato", "call_response"],
    "tension": ["sequence_up", "augment", "call_response", "climax"],
    "release": ["climax", "resolve", "sparse", "pedal"],
    "climax": ["climax", "augment", "call_response", "sequence_up", "climax"],
    "reflection": ["fragment", "sparse", "pedal", "introduce"],
    "transition": ["expand", "sequence_up", "call_response", "introduce"],
    "silence": ["sparse", "pedal"],
}

# Carga de variación esperada por rol (no por género)
ROLE_VARIATION_WEIGHT: dict[str, float] = {
    "silence": 0.25,
    "reflection": 0.45,
    "establish": 0.55,
    "transition": 0.65,
    "release": 0.75,
    "tension": 0.9,
    "climax": 1.0,
}

# Loop = poca variación interna; game/cutscene = más micro-arcos en secciones largas
USE_CASE_VARIATION_BASE: dict[str, float] = {
    "loop": 0.35,
    "cutscene": 0.55,
    "animation": 0.65,
    "game": 0.9,
}

CONTOUR_OPTIONS = [
    "ascending", "descending", "arch", "zigzag", "wave", "saw", "static",
]

DEFAULT_MOTIF = [0, 2, 4, 2]

# Compases máximos por segmento antes de forzar otro micro-arco
MAX_BARS_PER_SEGMENT = {
    "loop": 12,
    "cutscene": 10,
    "animation": 8,
    "game": 8,
}


def _transform_motif(
    motif: list[int],
    transform: str,
    seed: int,
) -> list[int]:
    if not motif:
        motif = DEFAULT_MOTIF
    if transform == "introduce":
        return list(motif)
    if transform == "sequence_up":
        step = 1 + (seed % 2)
        return [(d + step) % 7 for d in motif]
    if transform == "sequence_down":
        return [(d - 1) % 7 for d in motif]
    if transform == "invert":
        return [(6 - d) % 7 for d in motif]
    if transform == "fragment":
        half = max(1, len(motif) // 2)
        return list(motif[:half])
    if transform == "expand":
        return motif + [(d + 2) % 7 for d in motif]
    if transform == "climax":
        return [(d + (1 if i % 2 else 0)) % 7 for i, d in enumerate(motif)]
    if transform == "resolve":
        return [0 if i >= len(motif) - 1 else d for i, d in enumerate(motif)]
    if transform == "sparse":
        return [motif[0]] if motif else [0]
    if transform == "ostinato":
        return list(motif)
    if transform == "augment":
        return [(d * 2) % 7 for d in motif]
    if transform == "call_response":
        return [(d + (seed % 3)) % 7 for d in motif]
    if transform == "pedal":
        return [0] + [(d + 1) % 7 for d in motif[1:]]
    return list(motif)


def _phrase_length(density: float, seed: int, *, segment_index: int = 0) -> int:
    base = 2 + (seed % 2)
    if density >= 0.85:
        base = 2
    elif density < 0.35:
        base = 2 + (seed % 2)
    else:
        base = 2 + (seed % 3)
    # Segmentos posteriores: frases más cortas → más cambio perceptible
    if segment_index >= 2:
        return max(2, base - 1)
    return base


def _contour_for_role(role: str, seed: int, energy_level: int = 3, segment_index: int = 0) -> str:
    if role in ("climax", "tension"):
        if energy_level >= 4:
            opts = ("saw", "zigzag", "wave")
            return opts[(seed + segment_index) % len(opts)]
        if energy_level <= 2:
            return "arch" if (seed + segment_index) % 2 else "wave"
        return CONTOUR_OPTIONS[(seed + segment_index) % 4]
    if role in ("reflection", "silence"):
        return "wave" if (seed + segment_index) % 2 else "static"
    if role == "transition":
        return CONTOUR_OPTIONS[(seed + segment_index + 3) % len(CONTOUR_OPTIONS)]
    return CONTOUR_OPTIONS[(seed + segment_index + 2) % len(CONTOUR_OPTIONS)]


def variation_need(
    *,
    use_case: str,
    narrative_role: str,
    density: float,
) -> float:
    """0–1: cuánta subdivisión interna merece la sección (independiente del género)."""
    uc = (use_case or "game").lower()
    base = USE_CASE_VARIATION_BASE.get(uc, 0.7)
    role_w = ROLE_VARIATION_WEIGHT.get(narrative_role, 0.6)
    density_factor = 0.45 + 0.55 * density
    return min(1.0, base * role_w * density_factor)


def segment_count_for_section(
    section_bars: int,
    *,
    use_case: str,
    narrative_role: str,
    density: float,
) -> int:
    """
    Número de subdivisiones de desarrollo dentro de la sección.
    Secciones cortas → 1 bloque; secciones largas (p. ej. drop de 1 min) → varios micro-arcos.
    """
    if section_bars <= 2:
        return 1

    need = variation_need(
        use_case=use_case,
        narrative_role=narrative_role,
        density=density,
    )
    uc = (use_case or "game").lower()
    max_seg_bars = MAX_BARS_PER_SEGMENT.get(uc, 8)

    # Mínimo de segmentos por longitud (evita un solo transform en 32+ compases)
    length_floor = 1
    if section_bars > max_seg_bars:
        length_floor = max(2, (section_bars + max_seg_bars - 1) // max_seg_bars)

    if section_bars <= 4:
        need_segments = 1
    elif section_bars <= 8:
        need_segments = 1 if need < 0.4 else 2
    elif section_bars <= 16:
        need_segments = max(2, int(1 + need * 2))
    elif section_bars <= 32:
        need_segments = max(2, int(2 + need * 2))
    else:
        need_segments = max(3, int(section_bars / max_seg_bars * (0.6 + need * 0.5)))

    count = max(length_floor, need_segments)
    # Loop: techo bajo aunque la sección sea larga
    if uc == "loop":
        count = min(count, max(1, section_bars // 12))
    return min(count, section_bars, 8)


def _segment_transforms(role: str, n_segments: int, seed: int) -> list[str]:
    progression = ROLE_SEGMENT_PROGRESSIONS.get(
        role,
        ROLE_SEGMENT_PROGRESSIONS["establish"],
    )
    if n_segments <= 1:
        return [ROLE_TO_TRANSFORM.get(role, "introduce")]

    base = ROLE_TO_TRANSFORM.get(role, "introduce")
    transforms: list[str] = []
    for i in range(n_segments):
        if i == 0:
            transforms.append(base)
        elif i == n_segments - 1 and role in ("climax", "tension"):
            transforms.append("augment" if n_segments >= 2 else "climax")
        elif i == n_segments - 1 and role in ("release", "reflection"):
            transforms.append("resolve" if role == "release" else "sparse")
        else:
            pick = progression[(i + seed) % len(progression)]
            if pick == base and len(progression) > 1:
                pick = progression[(i + seed + 1) % len(progression)]
            transforms.append(pick)
    if n_segments > 2 and len(set(transforms)) < 2:
        mid = n_segments // 2
        transforms[mid] = progression[(seed + 2) % len(progression)]
    return transforms


def _segment_boundaries(section_bars: int, n_segments: int) -> list[tuple[int, int]]:
    if n_segments <= 1:
        return [(0, section_bars)]
    base = section_bars // n_segments
    remainder = section_bars % n_segments
    bounds: list[tuple[int, int]] = []
    start = 0
    for i in range(n_segments):
        span = base + (1 if i < remainder else 0)
        end = min(section_bars, start + span)
        if end > start:
            bounds.append((start, end))
        start = end
    if bounds and bounds[-1][1] < section_bars:
        s, _ = bounds[-1]
        bounds[-1] = (s, section_bars)
    return bounds


def build_section_segments(
    section_id: str,
    section_bars: int,
    intent: SectionIntent | None,
    global_motif: list[int],
    seed: int,
    *,
    use_case: str = "game",
    energy_level: int = 3,
    transform_override: str | None = None,
    density_override: float | None = None,
    rhythmic_density_override: float | None = None,
) -> list[DevelopmentSegment]:
    role = intent.narrative_role if intent else "establish"
    base_density = intent.density if intent else 0.5
    if density_override is not None:
        base_density = density_override
    if rhythmic_density_override is not None:
        base_density = max(base_density, rhythmic_density_override)
    density = max(0.0, min(1.0, base_density))
    section_seed = (seed + hash(section_id)) % 9973
    motif = global_motif or DEFAULT_MOTIF

    n_seg = segment_count_for_section(
        section_bars,
        use_case=use_case,
        narrative_role=role,
        density=density,
    )
    bounds = _segment_boundaries(section_bars, n_seg)
    transforms = _segment_transforms(role, len(bounds), section_seed)
    valid_overrides = set(ROLE_TO_TRANSFORM.values()) | {
        "invert", "ostinato", "augment", "call_response", "pedal",
    }
    if transform_override and transform_override in valid_overrides:
        transforms[0] = transform_override

    segments: list[DevelopmentSegment] = []
    for idx, ((start, end), transform) in enumerate(zip(bounds, transforms)):
        seg_seed = (section_seed + idx * 17) % 9973
        segments.append(DevelopmentSegment(
            start_bar=start,
            end_bar=end,
            transform=transform,  # type: ignore[arg-type]
            phrase_length_bars=_phrase_length(density, seg_seed, segment_index=idx),
            contour=_contour_for_role(role, seg_seed, energy_level, segment_index=idx),
            motif_variant=_transform_motif(motif, transform, seg_seed + idx),
        ))
    return segments


def build_section_development(
    section_id: str,
    intent: SectionIntent | None,
    global_motif: list[int],
    seed: int,
    energy_level: int = 3,
    *,
    section_bars: int = 4,
    use_case: str = "game",
    transform_override: str | None = None,
    density_override: float | None = None,
    rhythmic_density_override: float | None = None,
) -> SectionDevelopment:
    role = intent.narrative_role if intent else "establish"
    density = intent.density if intent else 0.5
    if density_override is not None:
        density = density_override
    if rhythmic_density_override is not None:
        density = max(density, rhythmic_density_override)
    density = max(0.0, min(1.0, density))
    transform = ROLE_TO_TRANSFORM.get(role, "introduce")
    if transform_override:
        transform = transform_override
    section_seed = (seed + hash(section_id)) % 9973
    motif = global_motif or DEFAULT_MOTIF

    segments = build_section_segments(
        section_id,
        section_bars,
        intent,
        motif,
        seed,
        use_case=use_case,
        energy_level=energy_level,
        transform_override=transform_override,
        density_override=density_override,
        rhythmic_density_override=rhythmic_density_override,
    )

    # Resumen de sección = primer segmento (compatibilidad) o rol global si no hay split
    head = segments[0] if segments else None
    return SectionDevelopment(
        section_id=section_id,
        transform=head.transform if head else transform,  # type: ignore[arg-type]
        phrase_length_bars=head.phrase_length_bars if head else _phrase_length(density, section_seed),
        contour=head.contour if head else _contour_for_role(role, section_seed, energy_level),
        motif_variant=head.motif_variant if head and head.motif_variant else _transform_motif(
            motif, transform, section_seed,
        ),
        segments=segments if len(segments) > 1 else [],
    )


def development_for_bar(section_dev: SectionDevelopment, bar_idx: int) -> SectionDevelopment:
    """Devuelve parámetros de desarrollo activos en el compás relativo de la sección."""
    for seg in section_dev.segments:
        if seg.start_bar <= bar_idx < seg.end_bar:
            return SectionDevelopment(
                section_id=section_dev.section_id,
                transform=seg.transform,
                phrase_length_bars=seg.phrase_length_bars,
                contour=seg.contour,
                motif_variant=seg.motif_variant,
                segments=[],
            )
    return section_dev


def build_development_plan(
    sections: list[str],
    global_motif: list[int],
    narrative_sections: dict[str, SectionIntent] | None = None,
    generation_seed: int = 0,
    energy_level: int = 3,
    *,
    bars_per_section: dict[str, int] | None = None,
    use_case: str = "game",
    composition_archetype: str | None = None,
    section_intensity_curve: dict[str, float] | None = None,
    rhythmic_density_curve: dict[str, float] | None = None,
    motif_transform_plan: dict[str, str] | None = None,
) -> DevelopmentPlan:
    motif = global_motif or DEFAULT_MOTIF
    bars_map = bars_per_section or {}
    section_devs = [
        build_section_development(
            section_id=s,
            intent=narrative_sections.get(s) if narrative_sections else None,
            global_motif=motif,
            seed=generation_seed,
            energy_level=energy_level,
            section_bars=bars_map.get(s, 4),
            use_case=use_case,
            transform_override=(motif_transform_plan or {}).get(s),
            density_override=(section_intensity_curve or {}).get(s),
            rhythmic_density_override=(rhythmic_density_curve or {}).get(s),
        )
        for s in sections
    ]
    from cadence.music.texture_policy import infer_texture_mode

    texture_mode = infer_texture_mode(
        use_case=use_case,
        energy_level=energy_level,
        narrative_sections=narrative_sections,
        composition_archetype=composition_archetype,
    )

    plan = DevelopmentPlan(
        global_motif=motif,
        sections=section_devs,
        generation_seed=generation_seed,
        texture_mode=texture_mode,
    )
    from cadence.music.segment_variation import boost_texture_mode_for_segments

    boosted = boost_texture_mode_for_segments(
        plan.texture_mode,
        plan,
        use_case=use_case,
        energy_level=energy_level,
        narrative_sections=narrative_sections,
    )
    if boosted != plan.texture_mode:
        plan = plan.model_copy(update={"texture_mode": boosted})
    return plan


def section_development_map(plan: DevelopmentPlan | None) -> dict[str, SectionDevelopment]:
    if not plan:
        return {}
    return {s.section_id: s for s in plan.sections}


def format_section_development_hint(section_dev: SectionDevelopment, section_bars: int) -> str:
    """Texto para el compositor LLM — subdivisiones si existen."""
    if not section_dev.segments:
        return (
            f"  - {section_dev.section_id} ({section_bars} bars): "
            f"transform={section_dev.transform}, frases {section_dev.phrase_length_bars} bars"
        )
    parts = []
    for seg in section_dev.segments:
        parts.append(
            f"bars {seg.start_bar}-{seg.end_bar - 1}: {seg.transform}, "
            f"frases {seg.phrase_length_bars} bars, contour={seg.contour}"
        )
    return f"  - {section_dev.section_id} ({section_bars} bars): " + "; ".join(parts)


def compute_generation_seed(raw_prompt: str, total_bars: int) -> int:
    from cadence.music.strategy_pools import compute_generation_seed as _seed
    return _seed(raw_prompt, total_bars)
