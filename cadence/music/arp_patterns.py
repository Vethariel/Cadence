"""Patrones de arpeggio deterministas sobre grados de acorde."""

from cadence.schemas.song_state import RhythmEvent
from cadence.music.pattern_registry import pattern_family, resolve_pattern_id

_ARP_BASE = (
    "up",
    "down",
    "pingpong",
    "updown",
    "cascade",
    "broken",
    "syncopated",
    "octave",
    "triplet",
    "sixteenth",
    "staccato",
    "spread",
)

_ARP_ALIASES: dict[str, str] = {fam: f"{fam}_a" for fam in _ARP_BASE}

ARP_PATTERNS: tuple[str, ...] = tuple(
    f"{fam}_{suffix}"
    for fam in _ARP_BASE
    for suffix in ("a", "b")
)


def pattern_for_seed(generation_seed: int) -> str:
    from cadence.music.pattern_selection import weighted_pick

    return weighted_pick(
        generation_seed, 17, list(ARP_PATTERNS), ARP_PATTERNS, field="arp",
    )


def resolve_arp_pattern(pattern_id: str | None, generation_seed: int = 0) -> str:
    if pattern_id:
        rid = resolve_pattern_id(pattern_id, _ARP_ALIASES, default="up_a")
        if rid in ARP_PATTERNS:
            return rid
    return pattern_for_seed(generation_seed)


def build_arp_pitch_sequence(pitches: list[int], pattern: str) -> list[int]:
    """Secuencia de alturas para un compás de arpeggio (3–8 notas del acorde)."""
    if len(pitches) < 3:
        pitches = pitches + [pitches[-1] + 12] if pitches else [60, 64, 67]

    root, third, fifth = pitches[0], pitches[1], pitches[2]
    high = [p + 12 for p in (root, third, fifth)]
    fam = pattern_family(pattern)
    variant = pattern.rsplit("_", 1)[-1] if "_" in pattern else "a"

    if fam == "up":
        if variant == "b":
            return [root, fifth, third, high[0], high[2], high[1]]
        return [root, third, fifth, high[0], high[1], high[2]]
    if fam == "down":
        if variant == "b":
            return [high[0], fifth, third, root, third, fifth]
        return [high[2], high[1], high[0], fifth, third, root]
    if fam == "pingpong":
        if variant == "b":
            return [root, fifth, high[1], fifth, root, third]
        return [root, third, fifth, high[1], fifth, third]
    if fam == "updown":
        if variant == "b":
            return [root, fifth, third, fifth, root, third]
        return [root, third, fifth, third, root, fifth]
    if fam == "cascade":
        if variant == "b":
            return [third, root, fifth, high[0], fifth, third]
        return [fifth, third, root, third, fifth, high[0]]
    if fam == "broken":
        if variant == "b":
            return [root, third, root, fifth, root, third]
        return [root, root, third, fifth, third, root]
    if fam == "syncopated":
        if variant == "b":
            return [fifth, root, high[0], third, fifth, root]
        return [root, fifth, third, high[0], fifth, third]
    if fam == "octave":
        if variant == "b":
            return [root, third, root + 12, fifth, third + 12, high[0]]
        return [root, root + 12, third, fifth, high[0], high[2]]
    if fam == "triplet":
        if variant == "b":
            return [root, fifth, third, fifth, root, fifth]
        return [root, third, fifth, root, third, fifth]
    if fam == "sixteenth":
        if variant == "b":
            return [root, fifth, third, fifth, high[0], high[1], high[2], fifth]
        return [root, third, fifth, third, fifth, high[0], high[1], high[2]]
    if fam == "staccato":
        if variant == "b":
            return [root, fifth, root, third, fifth, third]
        return [root, third, root, fifth, third, fifth]
    if fam == "spread":
        if variant == "b":
            return [root, high[0], third, high[1], fifth, high[2]]
        return [root, third, high[0], fifth, high[1], high[2]]
    return [root, third, fifth, high[0], high[1], high[2]]


def steps_per_note(
    density: float,
    rhythmic_complexity: float,
    pattern: str = "",
) -> int:
    """1 = corcheas, 2 = negras subdivididas en 8ths."""
    fam = pattern_family(pattern)
    if fam == "sixteenth":
        return 1
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