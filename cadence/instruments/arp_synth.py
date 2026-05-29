"""Arpeggio determinista sobre acordes — capa Spider Dance / Bad Apple."""

from cadence.agent.nodes.narrative_apply import section_intent_map
from cadence.instruments.context import ComposeContext
from cadence.instruments.registry import InstrumentDefinition, register
from cadence.music.arp_patterns import generate_bar_arp, steps_per_note
from cadence.music.harmony_theory import chord_at_bar, chord_pitches, section_harmony_map
from cadence.schemas.song_state import Track


def _ms_per_step(bpm: int) -> float:
    return (60000 / bpm) / 4


def _compose_arp_synth(ctx: ComposeContext) -> Track | None:
    harmony = ctx.state.get("harmony")
    if not harmony:
        return None

    structure = ctx.state["structure"]
    narrative = ctx.state.get("narrative")
    intent_map = section_intent_map(narrative)
    harmony_map = section_harmony_map(harmony)
    active = set(ctx.active_sections())

    strategies = ctx.state.get("strategies")
    pattern = (
        strategies.arp_pattern
        if strategies
        else "up"
    )

    step_ms = _ms_per_step(ctx.bpm)
    steps_per_bar = 16
    events = []
    current_t = 0.0
    beat_index = 0

    for section in structure.sections:
        bars = structure.bars_per_section.get(section, 4)
        intent = intent_map.get(section)
        density = intent.density if intent else 0.5
        rhythmic = intent.rhythmic_complexity if intent else 0.5

        if section not in active or density < 0.7:
            current_t += bars * steps_per_bar * step_ms
            beat_index += bars * steps_per_bar
            continue

        section_h = harmony_map.get(section)
        if not section_h:
            current_t += bars * steps_per_bar * step_ms
            beat_index += bars * steps_per_bar
            continue

        note_stride = steps_per_note(density, rhythmic)
        base_vel = int(38 + density * 28)

        for bar_idx in range(bars):
            chord = chord_at_bar(section_h, bar_idx)
            pitches = chord_pitches(ctx.key, ctx.mode, chord, octave=4)
            events.extend(generate_bar_arp(
                pitches=pitches,
                pattern=pattern,
                step_ms=step_ms,
                bar_start_t=current_t,
                beat_index=beat_index,
                section=section,
                base_velocity=base_vel,
                steps_per_bar=steps_per_bar,
                note_stride=note_stride,
            ))
            current_t += steps_per_bar * step_ms
            beat_index += steps_per_bar

    if not events:
        return None

    return Track(
        id="arp_synth",
        instrument_id="arp_synth",
        instrument="Arp Synth",
        midi_channel=6,
        role="lead",
        events=events,
    )


register(InstrumentDefinition(
    instrument_id="arp_synth",
    display_name="Arp Synth",
    role="lead",
    midi_channel=6,
    requires_llm=False,
    compose=_compose_arp_synth,
))
