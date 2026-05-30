"""Métricas de riqueza sobre tracks .rsong — usadas por el validador."""

from __future__ import annotations

import statistics
from collections import defaultdict

from cadence.schemas.song_state import Track

LEAD_IDS = frozenset({
    "melody", "countermelody", "echo_synth", "arp_synth", "chord_stab",
})


def ms_per_bar(bpm: int) -> float:
    return (60000 / max(bpm, 1)) * 4


def layers_active_stats(tracks: list[Track], bpm: int) -> tuple[float, int]:
    """Media y máximo de pistas con notas por compás global."""
    bar_ms = ms_per_bar(bpm)
    bar_active: dict[int, int] = defaultdict(int)

    for track in tracks:
        if not track.events:
            continue
        active_bars = {
            int(e.t // bar_ms)
            for e in track.events
            if e.type in ("note", "drum_hit")
        }
        for bar in active_bars:
            bar_active[bar] += 1

    if not bar_active:
        return 0.0, 0
    vals = list(bar_active.values())
    return statistics.mean(vals), max(vals)


def notes_per_bar_stdev(tracks: list[Track], bpm: int) -> float:
    """Desviación estándar de la densidad total de notas por compás."""
    bar_ms = ms_per_bar(bpm)
    bar_notes: dict[int, int] = defaultdict(int)

    for track in tracks:
        for e in track.events:
            if e.type in ("note", "drum_hit"):
                bar_notes[int(e.t // bar_ms)] += 1

    if len(bar_notes) < 2:
        return 0.0
    return statistics.stdev(bar_notes.values())


def melody_notes_per_bar_mean(tracks: list[Track], bpm: int) -> float:
    """Media de notas melódicas por compás con eventos."""
    melody = next((t for t in tracks if t.id == "melody"), None)
    if not melody or not melody.events:
        return 0.0
    bar_ms = ms_per_bar(bpm)
    bar_notes: dict[int, int] = defaultdict(int)
    for e in melody.events:
        if e.type == "note":
            bar_notes[int(e.t // bar_ms)] += 1
    if not bar_notes:
        return 0.0
    return statistics.mean(bar_notes.values())


def melody_leap_ratio(tracks: list[Track]) -> float:
    """Fracción de intervalos melódicos mayores a 4 semitonos."""
    melody = next((t for t in tracks if t.id == "melody"), None)
    if not melody or len(melody.events) < 2:
        return 0.0

    notes = sorted(
        (e for e in melody.events if e.type == "note"),
        key=lambda e: e.t,
    )
    if len(notes) < 2:
        return 0.0

    leaps = [
        abs(notes[i].pitch - notes[i - 1].pitch)
        for i in range(1, len(notes))
    ]
    return sum(1 for d in leaps if d > 4) / len(leaps)


def optional_layer_coverage(
    tracks: list[Track],
    instrument_id: str,
    duration_ms: int,
) -> float:
    """Cobertura temporal de una capa opcional (0–1)."""
    track = next((t for t in tracks if t.id == instrument_id), None)
    if not track or not track.events or duration_ms <= 0:
        return 0.0
    last = max(e.t + e.duration_ms for e in track.events)
    return last / duration_ms
