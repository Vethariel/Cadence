"""Desarrollo motivico determinista — transformaciones por sección narrativa."""

from cadence.schemas.song_state import DevelopmentPlan, SectionDevelopment, SectionIntent

ROLE_TO_TRANSFORM: dict[str, str] = {
    "establish": "introduce",
    "tension": "sequence_up",
    "release": "resolve",
    "climax": "climax",
    "reflection": "fragment",
    "transition": "expand",
    "silence": "sparse",
}

CONTOUR_OPTIONS = ["ascending", "descending", "arch", "zigzag", "wave"]

DEFAULT_MOTIF = [0, 2, 4, 2]


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
    return list(motif)


def _phrase_length(density: float, seed: int) -> int:
    if density < 0.35:
        return 2
    if density < 0.65:
        return 2 + (seed % 2)
    return 2 + (seed % 3)  # 2, 3, or 4


def _contour_for_role(role: str, seed: int) -> str:
    if role in ("climax", "tension"):
        return CONTOUR_OPTIONS[seed % 3]  # ascending, descending, arch
    if role in ("reflection", "silence"):
        return "wave"
    return CONTOUR_OPTIONS[(seed + 2) % len(CONTOUR_OPTIONS)]


def build_section_development(
    section_id: str,
    intent: SectionIntent | None,
    global_motif: list[int],
    seed: int,
) -> SectionDevelopment:
    role = intent.narrative_role if intent else "establish"
    density = intent.density if intent else 0.5
    transform = ROLE_TO_TRANSFORM.get(role, "introduce")
    section_seed = (seed + hash(section_id)) % 9973
    motif = global_motif or DEFAULT_MOTIF
    return SectionDevelopment(
        section_id=section_id,
        transform=transform,
        phrase_length_bars=_phrase_length(density, section_seed),
        contour=_contour_for_role(role, section_seed),
        motif_variant=_transform_motif(motif, transform, section_seed),
    )


def build_development_plan(
    sections: list[str],
    global_motif: list[int],
    narrative_sections: dict[str, SectionIntent] | None = None,
    generation_seed: int = 0,
) -> DevelopmentPlan:
    motif = global_motif or DEFAULT_MOTIF
    section_devs = [
        build_section_development(
            section_id=s,
            intent=narrative_sections.get(s) if narrative_sections else None,
            global_motif=motif,
            seed=generation_seed,
        )
        for s in sections
    ]
    return DevelopmentPlan(
        global_motif=motif,
        sections=section_devs,
        generation_seed=generation_seed,
    )


def section_development_map(plan: DevelopmentPlan | None) -> dict[str, SectionDevelopment]:
    if not plan:
        return {}
    return {s.section_id: s for s in plan.sections}


def compute_generation_seed(raw_prompt: str, total_bars: int) -> int:
    return abs(hash(f"{raw_prompt}:{total_bars}")) % 100_000
