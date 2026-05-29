"""Teoría armónica determinista compartida por bajo, pad y melodía."""

from cadence.schemas.song_state import ChordSpec, HarmonyPlan, SectionHarmony

SCALES = {
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "major": [0, 2, 4, 5, 7, 9, 11],
}

KEY_MIDI = {
    "C": 60, "C#": 61, "D": 62, "D#": 63, "E": 64, "F": 65,
    "F#": 66, "G": 67, "G#": 68, "A": 69, "A#": 70, "B": 71,
}

BASS_MIDI = {
    "C": 36, "C#": 37, "D": 38, "D#": 39, "E": 40, "F": 41,
    "F#": 42, "G": 43, "G#": 44, "A": 45, "A#": 46, "B": 47,
}

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
    return key.split()[0].capitalize()


def scale_pitches(key: str, mode: str, octave: int = 4) -> list[int]:
    root = KEY_MIDI.get(parse_key(key), 60) + (octave - 4) * 12
    intervals = SCALES.get(mode, SCALES["minor"])
    return [root + i for i in intervals]


def bass_root_midi(key: str) -> int:
    return BASS_MIDI.get(parse_key(key), 36)


def chord_pitches(
    key: str,
    mode: str,
    chord: ChordSpec,
    octave: int = 3,
) -> list[int]:
    """Tres notas del acorde en MIDI (root, third, fifth)."""
    root_base = bass_root_midi(key) + (octave - 2) * 12
    scale = SCALES.get(mode, SCALES["minor"])
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
) -> list[tuple[int, str]]:
    templates = PROGRESSIONS_MINOR if mode == "minor" else PROGRESSIONS_MAJOR
    base = ROLE_TO_TEMPLATE.get(narrative_role, "default")
    if harmonic_tension >= 0.75 and narrative_role in ("tension", "climax"):
        base = "tension"
    elif harmonic_tension <= 0.25:
        base = "sparse"
    return templates[base]


def build_section_harmony(
    section_id: str,
    narrative_role: str,
    harmonic_tension: float,
    mode: str,
    bars_per_chord: int = 4,
) -> SectionHarmony:
    raw = progression_for_role(narrative_role, harmonic_tension, mode)
    progression = [
        ChordSpec(root_degree=deg, quality=qual, bars=bars_per_chord)
        for deg, qual in raw
    ]
    return SectionHarmony(section_id=section_id, progression=progression)


def build_harmony_plan(
    sections: list[str],
    key: str,
    mode: str,
    narrative_sections: dict | None = None,
    bars_per_chord_default: int = 4,
) -> HarmonyPlan:
    """Genera HarmonyPlan determinista desde estructura + narrativa."""
    section_harmonies: list[SectionHarmony] = []

    for section_id in sections:
        intent = narrative_sections.get(section_id) if narrative_sections else None
        role = intent.narrative_role if intent else "establish"
        tension = intent.harmonic_tension if intent else 0.4
        bars_per_chord = 2 if tension >= 0.65 else bars_per_chord_default
        if role in ("climax", "reflection", "silence"):
            bars_per_chord = bars_per_chord_default

        section_harmonies.append(build_section_harmony(
            section_id=section_id,
            narrative_role=role,
            harmonic_tension=tension,
            mode=mode,
            bars_per_chord=bars_per_chord,
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
    nums = numerals_minor if mode == "minor" else numerals_major
    base = nums[chord.root_degree % 7]
    if chord.quality == "major" and base.islower() and base not in ("ii", "iv", "v"):
        return base.upper()
    if chord.quality == "minor" and base.isupper():
        return base.lower()
    if chord.quality == "dominant":
        return base.upper() + "7" if mode == "minor" else base
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
