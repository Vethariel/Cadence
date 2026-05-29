"""Contramelodía determinista — segunda voz derivada del motivo en desarrollo."""

from cadence.instruments.context import ComposeContext
from cadence.instruments.registry import InstrumentDefinition, register
from cadence.agent.nodes.narrative_apply import section_intent_map, melody_should_play
from cadence.music.development_theory import section_development_map
from cadence.music.harmony_theory import chord_at_bar, chord_tones_as_degrees, section_harmony_map
from cadence.schemas.song_state import RhythmEvent, Track

OFFBEAT_STEPS = (4, 6, 12, 14)


def _ms_per_step(bpm: int) -> float:
    return (60000 / bpm) / 4


def _compose_countermelody(ctx: ComposeContext) -> Track | None:
    structure = ctx.state["structure"]
    narrative = ctx.state.get("narrative")
    development = ctx.state.get("development")
    harmony = ctx.state.get("harmony")

    if not development:
        return None

    intent_map = section_intent_map(narrative)
    dev_map = section_development_map(development)
    harmony_map = section_harmony_map(harmony)
    active = set(ctx.active_sections())

    from cadence.agent.nodes.melody import _get_scale_pitches
    scale_pitches = _get_scale_pitches(ctx.key, ctx.mode)

    step_ms = _ms_per_step(ctx.bpm)
    steps_per_bar = 16
    events: list[RhythmEvent] = []
    current_t = 0.0
    beat_index = 0

    for section in structure.sections:
        bars = structure.bars_per_section.get(section, 4)
        intent = intent_map.get(section)
        dev = dev_map.get(section)

        if section not in active or not melody_should_play(intent) or not dev:
            current_t += bars * steps_per_bar * step_ms
            beat_index += bars * steps_per_bar
            continue

        density = intent.density if intent else 0.5
        if density < 0.45:
            current_t += bars * steps_per_bar * step_ms
            beat_index += bars * steps_per_bar
            continue

        motif = dev.motif_variant or development.global_motif or [0, 2, 4]
        base_vel = int(45 + density * 35)

        for bar_idx in range(bars):
            section_h = harmony_map.get(section)
            chord_degrees = motif
            if section_h:
                chord = chord_at_bar(section_h, bar_idx)
                chord_degrees = chord_tones_as_degrees(chord)

            for step_i, step in enumerate(OFFBEAT_STEPS):
                degree = chord_degrees[step_i % len(chord_degrees)] % 7
                if dev.transform == "invert":
                    degree = (6 - degree) % 7
                pitch = scale_pitches[degree] - 12
                pitch = max(21, min(108, pitch))
                events.append(RhythmEvent(
                    t=int(current_t + step * step_ms),
                    type="note",
                    pitch=pitch,
                    duration_ms=int(step_ms * 1.2),
                    velocity=base_vel,
                    beat_index=beat_index + step,
                    section=section,
                ))

            current_t += steps_per_bar * step_ms
            beat_index += steps_per_bar

    if not events:
        return None

    return Track(
        id="countermelody",
        instrument_id="countermelody",
        instrument="Counter Melody",
        midi_channel=4,
        role="lead",
        events=events,
    )


register(InstrumentDefinition(
    instrument_id="countermelody",
    display_name="Counter Melody",
    role="lead",
    midi_channel=4,
    requires_llm=False,
    compose=_compose_countermelody,
))
