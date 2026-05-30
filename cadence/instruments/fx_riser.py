"""FX de transición — risers y sweeps en último compás de sección."""

from cadence.music.meter_theory import ms_per_step, steps_per_bar as meter_steps_per_bar
from cadence.instruments.context import ComposeContext
from cadence.instruments.registry import InstrumentDefinition, register
from cadence.music.narrative_contract import section_intent_map_from_state
from cadence.music.seed_policy import seed_for_state
from cadence.schemas.song_state import RhythmEvent, Track

FX_TRANSITIONS = {"riser", "filter_sweep", "pickup"}
DRUM_MIDI = {"snare": 38, "hihat": 42}



def _compose_fx_riser(ctx: ComposeContext) -> Track | None:
    structure = ctx.state["structure"]
    narrative = ctx.state.get("narrative")
    if not narrative:
        return None

    seed = seed_for_state(ctx.state, "fx_riser") or ctx.state.get("generation_seed", 0)
    intent_map = section_intent_map_from_state(ctx.state, context="fx_riser")
    active = set(ctx.active_sections())
    step_ms = ms_per_step(ctx.bpm, ctx.time_signature)
    steps_per_bar = meter_steps_per_bar(ctx.time_signature)
    events: list[RhythmEvent] = []
    current_t = 0.0
    beat_index = 0

    for section in structure.sections:
        bars = structure.bars_per_section.get(section, 4)
        intent = intent_map.get(section)

        if section not in active or not intent or intent.transition_out not in FX_TRANSITIONS:
            current_t += bars * steps_per_bar * step_ms
            beat_index += bars * steps_per_bar
            continue

        for bar_idx in range(bars):
            if bar_idx == bars - 1:
                t_bar = current_t
                trans = intent.transition_out
                if trans == "riser":
                    for step in range(steps_per_bar):
                        pitch = 48 + int(step * 1.5) + (seed % 5)
                        vel = 40 + int(step / steps_per_bar * 80)
                        events.append(RhythmEvent(
                            t=int(t_bar + step * step_ms),
                            type="note",
                            pitch=min(84, pitch),
                            duration_ms=int(step_ms * 0.8),
                            velocity=min(127, vel),
                            beat_index=beat_index + step,
                            section=section,
                        ))
                elif trans == "filter_sweep":
                    for step in range(steps_per_bar):
                        pitch = 36 + step * 2
                        events.append(RhythmEvent(
                            t=int(t_bar + step * step_ms),
                            type="note",
                            pitch=min(72, pitch),
                            duration_ms=int(step_ms * 0.6),
                            velocity=30 + step * 5,
                            beat_index=beat_index + step,
                            section=section,
                        ))
                elif trans == "pickup":
                    for step in (8, 10, 12, 14, 15):
                        events.append(RhythmEvent(
                            t=int(t_bar + step * step_ms),
                            type="drum_hit",
                            pitch=DRUM_MIDI["snare"],
                            duration_ms=int(step_ms * 0.7),
                            velocity=70 + step * 3,
                            beat_index=beat_index + step,
                            section=section,
                        ))

            current_t += steps_per_bar * step_ms
            beat_index += steps_per_bar

    if not events:
        return None

    return Track(
        id="fx_riser",
        instrument_id="fx_riser",
        instrument="FX Riser",
        midi_channel=3,
        role="fx",
        events=events,
    )


register(InstrumentDefinition(
    instrument_id="fx_riser",
    display_name="FX Riser",
    role="fx",
    midi_channel=3,
    requires_llm=False,
    compose=_compose_fx_riser,
))
