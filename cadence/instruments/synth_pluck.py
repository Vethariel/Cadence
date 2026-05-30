"""Plucks rítmicos de una nota — raíz del acorde, capa de groove."""

from cadence.music.meter_theory import ms_per_step, steps_per_bar as meter_steps_per_bar
from cadence.instruments.context import ComposeContext
from cadence.music.narrative_contract import section_intent_map_from_state
from cadence.music.seed_policy import seed_for_state
from cadence.instruments.registry import InstrumentDefinition, register
from cadence.music.harmony_theory import chord_at_bar, chord_pitches, section_harmony_map
from cadence.music.instrument_patterns import pluck_steps
from cadence.schemas.song_state import RhythmEvent, Track



def _compose_synth_pluck(ctx: ComposeContext) -> Track | None:
    harmony = ctx.state.get("harmony")
    if not harmony:
        return None

    structure = ctx.state["structure"]
    intent_map = section_intent_map_from_state(ctx.state, context="synth_pluck")
    harmony_map = section_harmony_map(harmony)
    active = set(ctx.active_sections())
    strategies = ctx.state.get("strategies")
    seed = seed_for_state(ctx.state, "synth_pluck") or ctx.state.get("generation_seed", 0)
    pluck_pattern = strategies.pluck_pattern if strategies else None
    steps = pluck_steps(pluck_pattern, seed)

    step_ms = ms_per_step(ctx.bpm, ctx.time_signature)
    steps_per_bar = meter_steps_per_bar(ctx.time_signature)
    events: list[RhythmEvent] = []
    current_t = 0.0
    beat_index = 0

    for section in structure.sections:
        bars = structure.bars_per_section.get(section, 4)
        intent = intent_map.get(section)
        density = intent.density if intent else 0.5

        if section not in active or density < ctx.layer.min_density:
            current_t += bars * steps_per_bar * step_ms
            beat_index += bars * steps_per_bar
            continue

        section_h = harmony_map.get(section)
        if not section_h:
            current_t += bars * steps_per_bar * step_ms
            beat_index += bars * steps_per_bar
            continue

        base_vel = int(42 + density * 30)
        pluck_dur = int(step_ms * 0.35)

        for bar_idx in range(bars):
            chord = chord_at_bar(section_h, bar_idx)
            pitches = chord_pitches(ctx.key, ctx.mode, chord, octave=4)
            root = pitches[0]
            for step in steps:
                events.append(RhythmEvent(
                    t=int(current_t + step * step_ms),
                    type="note",
                    pitch=root,
                    duration_ms=pluck_dur,
                    velocity=base_vel,
                    beat_index=beat_index + step,
                    section=section,
                ))
            current_t += steps_per_bar * step_ms
            beat_index += steps_per_bar

    if not events:
        return None

    return Track(
        id="synth_pluck",
        instrument_id="synth_pluck",
        instrument="Synth Pluck",
        midi_channel=8,
        role="lead",
        events=events,
    )


register(InstrumentDefinition(
    instrument_id="synth_pluck",
    display_name="Synth Pluck",
    role="lead",
    midi_channel=8,
    requires_llm=False,
    compose=_compose_synth_pluck,
))
