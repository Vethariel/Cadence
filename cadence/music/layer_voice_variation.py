"""Variación de registro y densidad por micro-arco — contramelodía, pad, eco."""

from __future__ import annotations

from cadence.schemas.song_state import SectionDevelopment

# Desplazamiento en semitonos (octava ≈ 12) por transform de desarrollo
TRANSFORM_PITCH_SHIFT: dict[str, int] = {
    "sparse": 0,
    "fragment": 0,
    "pedal": -12,
    "resolve": -5,
    "introduce": 12,
    "ostinato": 7,
    "expand": 12,
    "call_response": 19,
    "sequence_up": 19,
    "sequence_down": 5,
    "invert": 12,
    "climax": 24,
    "augment": 24,
}

SPARSE_TRANSFORMS = frozenset({"sparse", "fragment", "pedal", "resolve"})


def pitch_shift_for_transform(transform: str, segment_index: int = 0) -> int:
    base = TRANSFORM_PITCH_SHIFT.get(transform, 12)
    # Alterna registro entre micro-arcos consecutivos
    return base + (segment_index % 2) * 7


def pad_octave_for_transform(transform: str, narrative_role: str) -> int:
    if transform in SPARSE_TRANSFORMS or narrative_role in ("reflection", "silence"):
        return 2
    if transform in ("climax", "augment", "call_response"):
        return 4
    if transform in ("expand", "sequence_up"):
        return 3
    return 3


def pad_velocity_scale(transform: str, narrative_role: str) -> float:
    if transform in SPARSE_TRANSFORMS or narrative_role == "reflection":
        return 0.72
    if transform in ("climax", "augment"):
        return 1.05
    return 1.0


def counter_skip_step(
    step_index: int,
    transform: str,
    *,
    texture_mode: str,
    events_per_bar: int,
) -> bool:
    """Reduce densidad en texturas bedded o transforms abiertos."""
    if texture_mode == "bedded" and step_index % 2 == 1:
        return True
    if transform in SPARSE_TRANSFORMS and step_index % 2 == 1:
        return True
    if events_per_bar > 6 and step_index % 3 == 2:
        return True
    return False


def echo_should_include_note(
    note_index: int,
    *,
    melody_notes_in_section: int,
    echo_notes_in_section: int,
    section_max_echo: int,
) -> bool:
    """Evita duplicar melodías muy densas (p. ej. climax)."""
    if echo_notes_in_section >= section_max_echo:
        return False
    if melody_notes_in_section >= 100:
        return note_index % 3 == 0
    if melody_notes_in_section >= 60:
        return note_index % 2 == 0
    return True


def section_echo_cap(
    *,
    energy_level: int,
    composition_archetype: str | None,
) -> int:
    arch = composition_archetype or ""
    if arch == "orchestral_boss" and energy_level >= 5:
        return 140
    if energy_level >= 5:
        return 100
    return 80
