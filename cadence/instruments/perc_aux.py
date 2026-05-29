"""Percusión auxiliar — claps y shakers en secciones densas."""

from cadence.instruments.context import ComposeContext
from cadence.instruments.registry import InstrumentDefinition, register
from cadence.agent.nodes.narrative_apply import section_intent_map
from cadence.schemas.song_state import RhythmEvent, Track

CLAP = 39
SHAKER = 42


def _ms_per_step(bpm: int) -> float:
    return (60000 / bpm) / 4


def _compose_perc_aux(ctx: ComposeContext) -> Track | None:
    structure = ctx.state["structure"]
    narrative = ctx.state.get("narrative")
    intent_map = section_intent_map(narrative)
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

        if section not in active or density < ctx.layer.min_density:
            current_t += bars * steps_per_bar * step_ms
            beat_index += bars * steps_per_bar
            continue

        vel = int(50 + density * 50)
        for _ in range(bars):
            for step in (4, 12):
                events.append(RhythmEvent(
                    t=int(current_t + step * step_ms),
                    type="drum_hit",
                    pitch=CLAP,
                    duration_ms=int(step_ms * 0.5),
                    velocity=vel,
                    beat_index=beat_index + step,
                    section=section,
                ))
            if density >= 0.7:
                for step in range(0, steps_per_bar, 4):
                    events.append(RhythmEvent(
                        t=int(current_t + step * step_ms),
                        type="drum_hit",
                        pitch=SHAKER,
                        duration_ms=int(step_ms * 0.3),
                        velocity=max(30, vel - 25),
                        beat_index=beat_index + step,
                        section=section,
                    ))
            current_t += steps_per_bar * step_ms
            beat_index += steps_per_bar

    if not events:
        return None

    return Track(
        id="perc_aux",
        instrument_id="perc_aux",
        instrument="Percussion Aux",
        midi_channel=10,
        role="rhythm",
        events=events,
    )


register(InstrumentDefinition(
    instrument_id="perc_aux",
    display_name="Percussion Aux",
    role="rhythm",
    midi_channel=10,
    requires_llm=False,
    compose=_compose_perc_aux,
))
