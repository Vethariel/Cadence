"""Teoría armónica determinista compartida por bajo, pad y melodía."""

from cadence.schemas.song_state import ChordSpec, HarmonyPlan, SectionHarmony
from cadence.music.scale_theory import (
    KEY_MIDI_BASS as BASS_MIDI,
    KEY_MIDI_ROOT as KEY_MIDI,
    bass_root_midi,
    harmony_template_key,
    parse_key_name,
    scale_pitches as _scale_pitches,
    scale_semitones,
)

QUALITY_INTERVALS = {
    "minor": [0, 3, 7],
    "major": [0, 4, 7],
    "dim": [0, 3, 6],
    "dominant": [0, 4, 7],
}

# Grados de escala como raíz (0-6)
PROGRESSIONS_MINOR = {
    "default": [(0, "minor"), (5, "major"), (2, "major"), (6, "major")],
    "tension": [(0, "minor"), (3, "minor"), (5, "major"), (4, "dominant")],
    "climax": [(0, "minor"), (0, "minor"), (6, "major"), (5, "major")],
    "sparse": [(0, "minor")],
    "release": [(0, "minor"), (5, "major"), (3, "minor"), (0, "minor")],
}

PROGRESSIONS_MAJOR = {
    "default": [(0, "major"), (4, "major"), (5, "minor"), (3, "major")],
    "tension": [(0, "major"), (5, "minor"), (3, "minor"), (4, "major")],
    "climax": [(0, "major"), (0, "major"), (5, "major"), (4, "major")],
    "sparse": [(0, "major")],
    "release": [(0, "major"), (4, "major"), (5, "minor"), (0, "major")],
}

ROLE_TO_TEMPLATE = {
    "establish": "default",
    "tension": "tension",
    "release": "release",
    "climax": "climax",
    "reflection": "sparse",
    "transition": "tension",
    "silence": "sparse",
}


def parse_key(key: str) -> str:
    return parse_key_name(key)


def scale_pitches(key: str, mode: str, octave: int = 4) -> list[int]:
    return _scale_pitches(key, mode, octave=octave)


def chord_pitches(
    key: str,
    mode: str,
    chord: ChordSpec,
    octave: int = 3,
) -> list[int]:
    """Tres notas del acorde en MIDI (root, third, fifth)."""
    root_base = bass_root_midi(key) + (octave - 2) * 12
    scale = scale_semitones(mode)
    root_semi = scale[chord.root_degree % 7]
    root = root_base + root_semi
    intervals = QUALITY_INTERVALS[chord.quality]
    return [root + i for i in intervals]


def chord_tones_as_degrees(chord: ChordSpec) -> list[int]:
    """Grados de escala que forman el acorde (root, third, fifth aprox)."""
    third = (chord.root_degree + 2) % 7
    fifth = (chord.root_degree + 4) % 7
    return [chord.root_degree, third, fifth]


def progression_for_role(
    narrative_role: str,
    harmonic_tension: float,
    mode: str,
    harmony_pool: str | None = None,
) -> list[tuple[int, str]]:
    if harmony_pool:
        from cadence.music.strategy_pools import get_harmony_templates
        templates = get_harmony_templates(harmony_template_key(mode), harmony_pool)
    else:
        templates = (
            PROGRESSIONS_MINOR
            if harmony_template_key(mode) == "minor"
            else PROGRESSIONS_MAJOR
        )
    base = ROLE_TO_TEMPLATE.get(narrative_role, "default")
    if harmonic_tension >= 0.75 and narrative_role in ("tension", "climax"):
        base = "tension"
    elif harmonic_tension <= 0.25:
        base = "sparse"
    return templates[base]


def _bars_per_chord(
    harmonic_tension: float,
    narrative_role: str,
    default: int = 4,
) -> int:
    """Ritmo armónico más rápido bajo tensión (1–2 compases por acorde)."""
    if narrative_role in ("reflection", "silence"):
        return default
    if narrative_role == "climax" and harmonic_tension >= 0.6:
        return 1
    if harmonic_tension >= 0.8:
        return 1
    if harmonic_tension >= 0.5:
        return 2
    if harmonic_tension >= 0.35:
        return 2
    return default


def build_section_harmony(
    section_id: str,
    narrative_role: str,
    harmonic_tension: float,
    mode: str,
    bars_per_chord: int = 4,
    harmony_pool: str | None = None,
) -> SectionHarmony:
    raw = progression_for_role(narrative_role, harmonic_tension, mode, harmony_pool)
    progression = [
        ChordSpec(root_degree=deg, quality=qual, bars=bars_per_chord)
        for deg, qual in raw
    ]
    return SectionHarmony(section_id=section_id, progression=progression)


def _loop_progression(mode: str, bars_per_chord: int) -> list[ChordSpec]:
    """Al menos dos cambios de acorde en loops (benchmark: chord_changes > 0)."""
    if harmony_template_key(mode) == "minor":
        raw = [(0, "minor"), (5, "major"), (3, "minor"), (4, "dominant")]
    else:
        raw = [(0, "major"), (4, "major"), (5, "minor"), (3, "major")]
    return [ChordSpec(root_degree=d, quality=q, bars=bars_per_chord) for d, q in raw]


def build_harmony_plan(
    sections: list[str],
    key: str,
    mode: str,
    narrative_sections: dict | None = None,
    bars_per_chord_default: int = 4,
    harmony_pool: str | None = None,
    use_case: str = "game",
) -> HarmonyPlan:
    """Genera HarmonyPlan determinista desde estructura + narrativa."""
    section_harmonies: list[SectionHarmony] = []
    uc = (use_case or "game").lower()
    loop_default = 2 if uc == "loop" else bars_per_chord_default

    for section_id in sections:
        intent = narrative_sections.get(section_id) if narrative_sections else None
        role = intent.narrative_role if intent else "establish"
        tension = intent.harmonic_tension if intent else 0.4
        bars_per_chord = _bars_per_chord(tension, role, loop_default)

        if uc == "loop" and role in ("reflection", "silence", "establish"):
            progression = _loop_progression(mode, max(2, min(bars_per_chord, 4)))
            section_harmonies.append(SectionHarmony(
                section_id=section_id,
                progression=progression,
            ))
            continue

        section_harmonies.append(build_section_harmony(
            section_id=section_id,
            narrative_role=role,
            harmonic_tension=tension,
            mode=mode,
            bars_per_chord=bars_per_chord,
            harmony_pool=harmony_pool,
        ))

    return HarmonyPlan(
        key=key,
        mode=mode,
        sections=section_harmonies,
        bars_per_chord_default=bars_per_chord_default,
    )


def section_harmony_map(plan: HarmonyPlan | None) -> dict[str, SectionHarmony]:
    if not plan:
        return {}
    return {s.section_id: s for s in plan.sections}


def chord_at_bar(section_harmony: SectionHarmony, bar_idx: int) -> ChordSpec:
    """Acorde activo en un compás dado (índice 0-based dentro de la sección)."""
    bar_cursor = 0
    while True:
        for chord in section_harmony.progression:
            if bar_idx < bar_cursor + chord.bars:
                return chord
            bar_cursor += chord.bars
        bar_idx = bar_idx % max(1, bar_cursor)


def roman_numeral(chord: ChordSpec, mode: str) -> str:
    numerals_minor = ["i", "ii", "III", "iv", "v", "VI", "VII"]
    numerals_major = ["I", "ii", "iii", "IV", "V", "vi", "vii"]
    nums = numerals_minor if harmony_template_key(mode) == "minor" else numerals_major
    base = nums[chord.root_degree % 7]
    if chord.quality == "major" and base.islower() and base not in ("ii", "iv", "v"):
        return base.upper()
    if chord.quality == "minor" and base.isupper():
        return base.lower()
    if chord.quality == "dominant":
        return base.upper() + "7" if harmony_template_key(mode) == "minor" else base
    return base


def harmony_summary_for_section(
    plan: HarmonyPlan,
    section_id: str,
) -> str:
    sh = section_harmony_map(plan).get(section_id)
    if not sh:
        return ""
    parts = [roman_numeral(c, plan.mode) for c in sh.progression]
    return " → ".join(parts)
