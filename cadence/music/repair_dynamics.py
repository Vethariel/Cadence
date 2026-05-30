"""Reparación determinista de dinámica e intensidad narrativa (post_process)."""

from __future__ import annotations

from cadence.music.crescendo import (
    apply_crescendo,
    apply_crescendo_to_event,
    section_velocity_multipliers,
)
from cadence.schemas.song_state import RhythmEvent, SongStructure, Track


def _section_avg_velocity(tracks: list[Track], sections: list[str]) -> dict[str, float]:
    buckets: dict[str, list[int]] = {s: [] for s in sections}
    for track in tracks:
        for e in track.events:
            if e.type in ("note", "drum_hit") and e.section in buckets:
                buckets[e.section].append(e.velocity)
    return {
        s: sum(v) / len(v)
        for s, v in buckets.items()
        if v
    }


def apply_repair_dynamic_range(
    tracks: list[Track],
    structure: SongStructure,
    bpm: int,
    narrative_sections: dict | None,
    *,
    spread_boost: float = 1.45,
) -> list[Track]:
    """
    Re-aplica crescendo con multiplicadores más contrastados entre secciones.
    """
    base = section_velocity_multipliers(structure.sections, narrative_sections)
    if not base:
        return apply_crescendo(tracks, structure, bpm, narrative_sections)

    lo = min(base.values())
    hi = max(base.values())
    mid = (lo + hi) / 2
    boosted = {}
    for sid, mult in base.items():
        if mult >= mid:
            boosted[sid] = min(1.22, mult * spread_boost)
        else:
            boosted[sid] = max(0.58, mult / spread_boost)

    result: list[Track] = []
    for track in tracks:
        events = [
            apply_crescendo_to_event(e, boosted.get(e.section, 1.0), structure, bpm)
            for e in track.events
        ]
        result.append(track.model_copy(update={"events": events}))
    return result


def apply_repair_intensity_arc(
    tracks: list[Track],
    structure: SongStructure,
    bpm: int,
    narrative_sections: dict | None,
) -> list[Track]:
    """
    Refuerza velocity en la sección de mayor density narrativa y atenúa las más bajas.
    """
    if not narrative_sections or len(structure.sections) < 2:
        return tracks

    target_density = {
        s: narrative_sections[s].density
        for s in structure.sections
        if s in narrative_sections
    }
    if not target_density:
        return tracks

    actual = _section_avg_velocity(tracks, structure.sections)
    if len(actual) < 2:
        return tracks

    peak_target = max(target_density, key=target_density.get)
    quiet_target = min(target_density, key=target_density.get)
    margin = 5.0

    if actual.get(peak_target, 0) >= actual.get(quiet_target, 0) + margin:
        return tracks

    boosts: dict[str, float] = {}
    for sid in structure.sections:
        d = target_density.get(sid, 0.5)
        if sid == peak_target:
            boosts[sid] = 1.14
        elif sid == quiet_target or d <= 0.35:
            boosts[sid] = 0.88
        elif d >= 0.65:
            boosts[sid] = 1.06
        else:
            boosts[sid] = 1.0

    result: list[Track] = []
    for track in tracks:
        events: list[RhythmEvent] = []
        for e in track.events:
            if e.type == "rest":
                events.append(e)
                continue
            mult = boosts.get(e.section, 1.0)
            vel = max(1, min(127, int(e.velocity * mult)))
            events.append(e.model_copy(update={"velocity": vel}))
        result.append(track.model_copy(update={"events": events}))
    return result
