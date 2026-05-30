"""Modos de escala y helpers compartidos (melodía, armonía, bajo)."""

from __future__ import annotations

from typing import Literal

ScaleMode = Literal["major", "minor", "dorian", "phrygian"]

SCALE_MODES: tuple[ScaleMode, ...] = ("major", "minor", "dorian", "phrygian")

# Intervalos en semitonos desde la tónica (octava incluida implícita vía %7)
SCALE_INTERVALS: dict[str, list[int]] = {
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "major": [0, 2, 4, 5, 7, 9, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
}

KEY_MIDI_ROOT = {
    "C": 60, "C#": 61, "D": 62, "D#": 63, "E": 64, "F": 65,
    "F#": 66, "G": 67, "G#": 68, "A": 69, "A#": 70, "B": 71,
}

KEY_MIDI_BASS = {
    "C": 36, "C#": 37, "D": 38, "D#": 39, "E": 40, "F": 41,
    "F#": 42, "G": 43, "G#": 44, "A": 45, "A#": 46, "B": 47,
}

_MODE_ALIASES: dict[str, ScaleMode] = {
    "maj": "major",
    "major": "major",
    "ionian": "major",
    "min": "minor",
    "minor": "minor",
    "aeolian": "minor",
    "natural minor": "minor",
    "dorian": "dorian",
    "dorico": "dorian",
    "phrygian": "phrygian",
    "frigio": "phrygian",
    "frigian": "phrygian",
}

# Grilla de bajo en semitonos (16 steps) cuando no hay plan armónico
_BASS_GRID: dict[str, list[int]] = {
    "minor": [0, 0, 3, 0, 5, 0, 7, 0, 0, 0, 3, 0, 7, 0, 5, 0],
    "major": [0, 0, 4, 0, 5, 0, 7, 0, 0, 0, 4, 0, 7, 0, 5, 0],
    "dorian": [0, 0, 3, 0, 5, 0, 9, 0, 0, 0, 3, 0, 9, 0, 5, 0],
    "phrygian": [0, 0, 1, 0, 5, 0, 7, 0, 0, 0, 1, 0, 7, 0, 5, 0],
}


def normalize_mode(raw: str | None) -> ScaleMode:
    key = (raw or "minor").strip().lower()
    if key in SCALE_MODES:
        return key  # type: ignore[return-value]
    return _MODE_ALIASES.get(key, "minor")


def parse_key_name(key: str) -> str:
    return key.split()[0].capitalize()


def scale_semitones(mode: str) -> list[int]:
    return SCALE_INTERVALS.get(normalize_mode(mode), SCALE_INTERVALS["minor"])


def harmony_template_key(mode: str) -> Literal["major", "minor"]:
    """Pools de progresión armónica: modos menores naturales → plantillas minor."""
    m = normalize_mode(mode)
    return "major" if m == "major" else "minor"


def scale_pitches(key: str, mode: str, *, octave: int = 4) -> list[int]:
    root = KEY_MIDI_ROOT.get(parse_key_name(key), 60) + (octave - 4) * 12
    return [root + i for i in scale_semitones(mode)]


def bass_root_midi(key: str) -> int:
    return KEY_MIDI_BASS.get(parse_key_name(key), 36)


def bass_step_intervals(mode: str, steps: int = 16) -> list[int]:
    grid = _BASS_GRID.get(normalize_mode(mode), _BASS_GRID["minor"])
    return [grid[i % len(grid)] for i in range(steps)]


def format_modes_for_llm() -> str:
    return "major | minor | dorian | phrygian"
