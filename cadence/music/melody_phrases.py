"""Utilidades de fraseo melódico — frases 2-4 compases y desarrollo motivico."""

from cadence.schemas.song_state import RhythmEvent, SectionDevelopment
from cadence.music.development_theory import development_for_bar


class MelodyNoteInputs:
    """Protocolo mínimo para notas melódicas (compatible con pydantic MelodyNote)."""

    scale_degree: int
    octave_offset: int
    duration_steps: int
    velocity: int
    is_rest: bool


def fix_phrase_steps(notes: list, total_steps: int) -> list:
    """Ajusta notas para que sumen exactamente total_steps."""
    if not notes:
        return notes
    total = sum(n.duration_steps for n in notes)
    if total == total_steps:
        return notes
    notes = list(notes)
    if total < total_steps:
        notes.append(notes[0].model_copy(update={
            "scale_degree": 0,
            "octave_offset": 0,
            "duration_steps": total_steps - total,
            "velocity": 80,
            "is_rest": True,
        }))
        return notes
    fixed = []
    acc = 0
    for note in notes:
        remaining = total_steps - acc
        if remaining <= 0:
            break
        if note.duration_steps > remaining:
            note = note.model_copy(update={"duration_steps": remaining})
        fixed.append(note)
        acc += note.duration_steps
    return fixed


def apply_development_to_notes(
    notes: list,
    dev: SectionDevelopment,
    cycle_idx: int,
    phrase_idx: int,
) -> list:
    """Transforma grados según plan de desarrollo y posición en el ciclo."""

    def shift_degree(degree: int) -> int:
        d = degree
        if dev.transform == "invert":
            d = (6 - d) % 7
        elif dev.transform == "sequence_up":
            d = (d + 1 + cycle_idx) % 7
        elif dev.transform == "sequence_down":
            d = (d - 1 - cycle_idx) % 7
        elif dev.transform == "climax":
            d = (d + (cycle_idx % 2)) % 7
        elif dev.transform == "resolve":
            d = max(0, d - cycle_idx % 2)
        elif dev.transform == "sparse":
            return d if phrase_idx == 0 else d
        elif dev.transform == "ostinato":
            d = degree
        elif dev.transform == "augment":
            d = (d * 2) % 7
        elif dev.transform == "call_response":
            d = (d + phrase_idx + cycle_idx) % 7
        elif dev.transform == "pedal":
            d = 0 if phrase_idx == 0 else d
        else:
            d = (d + cycle_idx + phrase_idx) % 7

        if phrase_idx == 1 and dev.contour in ("arch", "zigzag"):
            d = (d + 2) % 7
        if dev.contour == "ascending":
            d = (d + phrase_idx) % 7
        elif dev.contour == "descending":
            d = (d - phrase_idx) % 7
        elif dev.contour == "saw":
            d = (d + phrase_idx - cycle_idx) % 7
        elif dev.contour == "static":
            pass

        return d % 7

    result = []
    for i, note in enumerate(notes):
        if note.is_rest:
            result.append(note)
            continue
        updates: dict = {"scale_degree": shift_degree(note.scale_degree)}
        if dev.transform == "climax" and cycle_idx > 0 and i % 2 == 0:
            updates["octave_offset"] = min(1, note.octave_offset + 1)
        if dev.transform == "fragment" and i >= len(notes) // 2:
            updates["is_rest"] = True
            updates["duration_steps"] = note.duration_steps
        result.append(note.model_copy(update=updates))
    return result


def apply_motif_bias(notes: list, motif: list[int], strength: float = 0.5) -> list:
    """Sesga grados hacia el motivo de la sección."""
    if not motif:
        return notes
    result = []
    note_idx = 0
    for note in notes:
        if note.is_rest:
            result.append(note)
            continue
        if note_idx < len(motif) and strength >= 0.5:
            result.append(note.model_copy(update={"scale_degree": motif[note_idx % len(motif)] % 7}))
            note_idx += 1
        else:
            result.append(note)
    return result


def phrases_to_events(
    phrases: list,
    section: str,
    total_bars: int,
    start_t: float,
    bpm: int,
    scale_pitches: list[int],
    beat_index_start: int,
    development: SectionDevelopment | None = None,
) -> tuple[list[RhythmEvent], float, int]:
    """Expande frases 2-4 compases cubriendo toda la sección con desarrollo."""
    step_ms = (60000 / bpm) / 4
    events: list[RhythmEvent] = []
    current_t = start_t
    beat_index = beat_index_start
    bar_idx = 0
    cycle_idx = 0

    if not phrases:
        return events, current_t + total_bars * 16 * step_ms, beat_index + total_bars * 16

    while bar_idx < total_bars:
        bar_dev = development_for_bar(development, bar_idx) if development else None
        for phrase_idx, phrase in enumerate(phrases):
            if bar_idx >= total_bars:
                break
            phrase_bars = min(phrase.bars, total_bars - bar_idx)
            total_steps = phrase_bars * 16
            pattern = fix_phrase_steps(phrase.pattern, total_steps)

            if bar_dev:
                pattern = apply_development_to_notes(pattern, bar_dev, cycle_idx, phrase_idx)
                if bar_dev.motif_variant:
                    pattern = apply_motif_bias(pattern, bar_dev.motif_variant, 0.4)

            for note in pattern:
                duration_ms = int(note.duration_steps * step_ms * 0.92)
                if not note.is_rest:
                    degree = max(0, min(6, note.scale_degree))
                    pitch = scale_pitches[degree] + note.octave_offset * 12
                    pitch = max(21, min(108, pitch))
                    events.append(RhythmEvent(
                        t=int(current_t),
                        type="note",
                        pitch=pitch,
                        duration_ms=duration_ms,
                        velocity=note.velocity,
                        beat_index=beat_index,
                        section=section,
                    ))
                current_t += note.duration_steps * step_ms
                beat_index += note.duration_steps

            bar_idx += phrase_bars

        cycle_idx += 1

    return events, current_t, beat_index
