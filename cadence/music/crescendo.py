"""Curvas de crescendo desde narrativa — escala velocity por sección y compás."""

from cadence.agent.nodes.narrative_apply import section_intent_map
from cadence.music.meter_theory import ms_per_bar as meter_ms_per_bar
from cadence.schemas.song_state import RhythmEvent, SongStructure, Track


def section_velocity_multipliers(
    sections: list[str],
    narrative_sections: dict | None,
) -> dict[str, float]:
    """Multiplicador de velocity por sección según density narrativa."""
    multipliers: dict[str, float] = {}
    for section_id in sections:
        intent = (narrative_sections or {}).get(section_id)
        density = intent.density if intent else 0.5
        role = intent.narrative_role if intent else "establish"
        base = 0.72 + density * 0.42
        if role == "climax":
            base = min(1.18, base + 0.08)
        elif role in ("reflection", "silence"):
            base = max(0.62, base - 0.12)
        multipliers[section_id] = round(base, 3)
    return multipliers


def _section_start_ms(
    section: str,
    structure: SongStructure,
    bpm: int,
    time_signature: list[int] | None = None,
) -> tuple[float, float]:
    """Retorna (inicio_ms, duración_ms) de una sección."""
    ms_per_bar = meter_ms_per_bar(bpm, time_signature)
    cursor = 0.0
    for sid in structure.sections:
        bars = structure.bars_per_section.get(sid, 4)
        duration = bars * ms_per_bar
        if sid == section:
            return cursor, duration
        cursor += duration
    return 0.0, 0.0


def bar_position_multiplier(
    t_ms: int,
    section: str,
    structure: SongStructure,
    bpm: int,
    time_signature: list[int] | None = None,
) -> float:
    """Micro-crescendo dentro de la sección (0.94 → 1.0)."""
    start_ms, duration_ms = _section_start_ms(section, structure, bpm, time_signature)
    if duration_ms <= 0:
        return 1.0
    progress = min(1.0, max(0.0, (t_ms - start_ms) / duration_ms))
    return 0.94 + progress * 0.06


def apply_crescendo_to_event(
    event: RhythmEvent,
    section_mult: float,
    structure: SongStructure,
    bpm: int,
    time_signature: list[int] | None = None,
) -> RhythmEvent:
    if event.type == "rest":
        return event
    bar_mult = bar_position_multiplier(
        event.t, event.section, structure, bpm, time_signature,
    )
    velocity = int(event.velocity * section_mult * bar_mult)
    velocity = max(1, min(127, velocity))
    return event.model_copy(update={"velocity": velocity})


def apply_crescendo(
    tracks: list[Track],
    structure: SongStructure,
    bpm: int,
    narrative_sections: dict | None,
    time_signature: list[int] | None = None,
) -> list[Track]:
    multipliers = section_velocity_multipliers(structure.sections, narrative_sections)
    result: list[Track] = []
    for track in tracks:
        events = [
            apply_crescendo_to_event(
                e, multipliers.get(e.section, 1.0), structure, bpm, time_signature,
            )
            for e in track.events
        ]
        result.append(track.model_copy(update={"events": events}))
    return result


def narrative_intensity_curve(
    sections: list[str],
    narrative_sections: dict | None,
) -> list[float]:
    """Curva de intensidad objetivo por sección (para export/meta)."""
    multipliers = section_velocity_multipliers(sections, narrative_sections)
    values = list(multipliers.values())
    if not values:
        return []
    lo, hi = min(values), max(values)
    span = hi - lo if hi > lo else 1.0
    return [round((multipliers[s] - lo) / span, 3) for s in sections]
