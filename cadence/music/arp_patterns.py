"""Patrones de arpeggio deterministas sobre grados de acorde."""

from cadence.schemas.song_state import RhythmEvent

ARP_PATTERNS = ("up", "down", "pingpong")


def pattern_for_seed(generation_seed: int) -> str:
    return ARP_PATTERNS[generation_seed % len(ARP_PATTERNS)]


def build_arp_pitch_sequence(pitches: list[int], pattern: str) -> list[int]:
    """Secuencia de alturas para un compás de arpeggio (3–6 notas del acorde)."""
    if len(pitches) < 3:
        pitches = pitches + [pitches[-1] + 12] if pitches else [60, 64, 67]

    root, third, fifth = pitches[0], pitches[1], pitches[2]
    high = [p + 12 for p in (root, third, fifth)]

    if pattern == "up":
        return [root, third, fifth, high[0], high[1], high[2]]
    if pattern == "down":
        return [high[2], high[1], high[0], fifth, third, root]
    return [root, third, fifth, high[1], fifth, third]


def steps_per_note(density: float, rhythmic_complexity: float) -> int:
    """1 = corcheas, 2 = negras subdivididas en 8ths."""
    if density >= 0.85 or rhythmic_complexity >= 0.65:
        return 1
    return 2


def generate_bar_arp(
    pitches: list[int],
    pattern: str,
    step_ms: float,
    bar_start_t: float,
    beat_index: int,
    section: str,
    base_velocity: int,
    steps_per_bar: int = 16,
    note_stride: int = 2,
) -> list[RhythmEvent]:
    """Genera un compás de arpeggio en semicorcheas u octavos."""
    seq = build_arp_pitch_sequence(pitches, pattern)
    events: list[RhythmEvent] = []
    step = 0
    seq_i = 0

    while step < steps_per_bar:
        pitch = seq[seq_i % len(seq)]
        vel = base_velocity + (seq_i % 3) * 4
        events.append(RhythmEvent(
            t=int(bar_start_t + step * step_ms),
            type="note",
            pitch=max(21, min(108, pitch)),
            duration_ms=int(step_ms * note_stride * 0.9),
            velocity=min(90, vel),
            beat_index=beat_index + step,
            section=section,
        ))
        seq_i += 1
        step += note_stride

    return events
