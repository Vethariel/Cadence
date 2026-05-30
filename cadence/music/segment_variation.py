"""Variación por micro-arco (DevelopmentSegment) — ritmo, armonía, textura y cues."""

from __future__ import annotations

from cadence.schemas.song_state import (
    ChordSpec,
    DevelopmentPlan,
    DevelopmentSegment,
    HarmonyPlan,
    SectionDevelopment,
    SectionHarmony,
    SectionIntent,
)

# Transform de desarrollo → plantilla armónica (más tensión / más reposo)
TRANSFORM_TO_HARMONY_TEMPLATE: dict[str, str] = {
    "introduce": "default",
    "expand": "default",
    "ostinato": "default",
    "sequence_up": "tension",
    "sequence_down": "release",
    "invert": "tension",
    "fragment": "sparse",
    "sparse": "sparse",
    "pedal": "sparse",
    "resolve": "release",
    "climax": "climax",
    "augment": "climax",
    "call_response": "tension",
}

# Transforms que rotan a una variante más ligera del patrón base
SPARSE_PATTERN_TRANSFORMS = frozenset({
    "sparse", "fragment", "pedal", "resolve", "sequence_down",
})

DENSE_PATTERN_TRANSFORMS = frozenset({
    "climax", "augment", "call_response", "sequence_up", "expand",
})


def segment_cue_label(section_id: str, segment_index: int) -> str:
    """Etiqueta exportable: drop → drop_1, drop_2, …"""
    return f"{section_id}_{segment_index + 1}"


def max_segment_count(development: DevelopmentPlan | None) -> int:
    if not development:
        return 0
    return max((len(s.segments) for s in development.sections), default=0)


def section_has_micro_arcs(section_dev: SectionDevelopment | None) -> bool:
    return bool(section_dev and len(section_dev.segments) > 1)


def segment_at_bar(section_dev: SectionDevelopment, bar_idx: int) -> DevelopmentSegment | None:
    for seg in section_dev.segments:
        if seg.start_bar <= bar_idx < seg.end_bar:
            return seg
    return None


def segment_index_at_bar(section_dev: SectionDevelopment, bar_idx: int) -> int:
    for idx, seg in enumerate(section_dev.segments):
        if seg.start_bar <= bar_idx < seg.end_bar:
            return idx
    return 0


def pattern_id_for_segment(
    base_pattern_id: str,
    segment_index: int,
    transform: str,
    seed: int,
    pool: list[str],
) -> str:
    """
    Variante del mismo patrón base: sub-variantes (_a/_b) o familia vecina en el pool.
    Mantiene coherencia (misma familia) pero cambia el groove entre micro-arcos.
    """
    from cadence.music.pattern_registry import expand_family_candidates, pattern_family

    if not base_pattern_id or segment_index <= 0:
        return base_pattern_id or (pool[0] if pool else base_pattern_id)

    variants = expand_family_candidates([base_pattern_id], pool)
    if len(variants) <= 1:
        return base_pattern_id

    fam = pattern_family(base_pattern_id)
    same_family = [v for v in variants if pattern_family(v) == fam]
    if len(same_family) <= 1:
        same_family = variants

    if transform in SPARSE_PATTERN_TRANSFORMS:
        # Variante más “abierta” dentro de la familia (índice bajo) o la base
        pick = same_family[0]
        return pick

    if transform in DENSE_PATTERN_TRANSFORMS:
        off = 1 + (seed + segment_index * 13) % max(1, len(same_family) - 1)
        return same_family[min(off, len(same_family) - 1)]

    off = (seed + segment_index * 7) % len(same_family)
    return same_family[off]


def _progression_for_segment(
    seg: DevelopmentSegment,
    seg_index: int,
    *,
    mode: str,
    harmonic_tension: float,
    harmony_pool: str | None,
    seed: int,
) -> list[ChordSpec]:
    from cadence.music.harmony_theory import progression_for_role

    template = TRANSFORM_TO_HARMONY_TEMPLATE.get(seg.transform, "default")
    raw = progression_for_role(template, harmonic_tension, mode, harmony_pool)
    seg_bars = max(1, seg.end_bar - seg.start_bar)
    n_chords = len(raw)
    if n_chords == 0:
        return [ChordSpec(root_degree=0, quality="minor" if mode == "minor" else "major", bars=seg_bars)]

    if seg.transform in ("sparse", "fragment", "pedal"):
        deg, qual = raw[0]
        return [ChordSpec(root_degree=deg, quality=qual, bars=seg_bars)]

    if harmonic_tension >= 0.7 or seg.transform in DENSE_PATTERN_TRANSFORMS:
        bars_per = max(1, seg_bars // max(n_chords, 2))
    else:
        bars_per = max(1, min(4, seg_bars // n_chords))

    chords: list[ChordSpec] = []
    cursor = 0
    idx = (seg_index + seed) % n_chords
    while cursor < seg_bars:
        deg, qual = raw[idx % n_chords]
        span = min(bars_per, seg_bars - cursor)
        chords.append(ChordSpec(root_degree=deg, quality=qual, bars=span))
        cursor += span
        idx += 1
    if chords and cursor < seg_bars:
        last = chords[-1]
        chords[-1] = ChordSpec(
            root_degree=last.root_degree,
            quality=last.quality,
            bars=last.bars + (seg_bars - cursor),
        )
    return chords


def enrich_harmony_with_segments(
    harmony: HarmonyPlan,
    development: DevelopmentPlan,
    narrative_sections: dict[str, SectionIntent] | None,
    *,
    seed: int = 0,
    harmony_pool: str | None = None,
) -> HarmonyPlan:
    """Fusiona progresiones por micro-arco en secciones con ≥2 segmentos."""
    narrative_sections = narrative_sections or {}
    dev_by_id = {s.section_id: s for s in development.sections}
    new_sections: list[SectionHarmony] = []

    for sh in harmony.sections:
        sec_dev = dev_by_id.get(sh.section_id)
        if not section_has_micro_arcs(sec_dev):
            new_sections.append(sh)
            continue

        intent = narrative_sections.get(sh.section_id)
        tension = intent.harmonic_tension if intent else 0.4
        progression: list[ChordSpec] = []
        for idx, seg in enumerate(sec_dev.segments):  # type: ignore[union-attr]
            progression.extend(_progression_for_segment(
                seg,
                idx,
                mode=harmony.mode,
                harmonic_tension=tension,
                harmony_pool=harmony_pool,
                seed=seed,
            ))
        new_sections.append(SectionHarmony(
            section_id=sh.section_id,
            progression=progression,
        ))

    return harmony.model_copy(update={"sections": new_sections})


def boost_texture_mode_for_segments(
    base_mode: str,
    development: DevelopmentPlan,
    *,
    use_case: str,
    energy_level: int,
    narrative_sections: dict[str, SectionIntent] | None = None,
) -> str:
    """Drops largos con micro-arcos → más solapamiento de capas opcionales."""
    if base_mode in ("bedded", "compact"):
        return base_mode
    uc = (use_case or "game").lower()
    if uc in ("loop", "cutscene") and max_segment_count(development) <= 2:
        return base_mode

    narrative_sections = narrative_sections or {}
    for sec_dev in development.sections:
        if len(sec_dev.segments) < 2:
            continue
        intent = narrative_sections.get(sec_dev.section_id)
        role = intent.narrative_role if intent else "establish"
        if role in ("climax", "tension") and energy_level >= 4:
            if base_mode == "staggered":
                return "simultaneous"
            return base_mode

    if max_segment_count(development) >= 3 and energy_level >= 4 and base_mode == "staggered":
        return "simultaneous"
    return base_mode
