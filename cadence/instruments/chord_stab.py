"""Stabs de acorde en offbeats — capa determinista de densidad armónica."""

from cadence.agent.nodes.narrative_apply import section_intent_map
from cadence.instruments.context import ComposeContext
from cadence.instruments.registry import InstrumentDefinition, register
from cadence.music.harmony_theory import chord_at_bar, chord_pitches, section_harmony_map
from cadence.schemas.song_state import RhythmEvent, Track

# Pasos 16th: beats 2 y 4 en 4/4
STAB_STEPS = (4, 8, 12)


def _ms_per_step(bpm: int) -> float:
    return (60000 / bpm) / 4


def _compose_chord_stab(ctx: ComposeContext) -> Track | None:
    harmony = ctx.state.get("harmony")
    if not harmony:
        return None

    structure = ctx.state["structure"]
    narrative = ctx.state.get("narrative")
    intent_map = section_intent_map(narrative)
    harmony_map = section_harmony_map(harmony)
    active = set(ctx.active_sections())

    step_ms = _ms_per_step(ctx.bpm)
    steps_per_bar = 16
    events: list[RhythmEvent] = []
    current_t = 0.0
    beat_index = 0

    for section in structure.sections:
        bars = structure.bars_per_section.get(section, 4)
        intent = intent_map.get(section)
        density = intent.density if intent else 0.5

        if section not in active or density < 0.45:
            current_t += bars * steps_per_bar * step_ms
            beat_index += bars * steps_per_bar
            continue

        section_h = harmony_map.get(section)
        if not section_h:
            current_t += bars * steps_per_bar * step_ms
            beat_index += bars * steps_per_bar
            continue

        base_vel = int(42 + density * 38)
        stab_dur = int(step_ms * 0.45)

        for bar_idx in range(bars):
            chord = chord_at_bar(section_h, bar_idx)
            pitches = chord_pitches(ctx.key, ctx.mode, chord, octave=5)
            for step in STAB_STEPS:
                t = current_t + step * step_ms
                for pitch in pitches:
                    events.append(RhythmEvent(
                        t=int(t),
                        type="note",
                        pitch=pitch,
                        duration_ms=stab_dur,
                        velocity=base_vel,
                        beat_index=beat_index + step,
                        section=section,
                    ))
            current_t += steps_per_bar * step_ms
            beat_index += steps_per_bar

    if not events:
        return None

    return Track(
        id="chord_stab",
        instrument_id="chord_stab",
        instrument="Chord Stab",
        midi_channel=7,
        role="lead",
        events=events,
    )


register(InstrumentDefinition(
    instrument_id="chord_stab",
    display_name="Chord Stab",
    role="lead",
    midi_channel=7,
    requires_llm=False,
    compose=_compose_chord_stab,
))
