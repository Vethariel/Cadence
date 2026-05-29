"""Eco determinista de la melodía — capa Spider Dance / Bad Apple."""

from cadence.instruments.context import ComposeContext
from cadence.instruments.registry import InstrumentDefinition, register
from cadence.music.layer_schedule import filter_events_by_schedule, ms_per_bar
from cadence.schemas.song_state import RhythmEvent, Track


def _compose_echo_synth(ctx: ComposeContext) -> Track | None:
    melody = next(
        (t for t in ctx.state.get("tracks", []) if t.id == "melody"),
        None,
    )
    if not melody or not melody.events:
        return None

    bar_ms = ms_per_bar(ctx.bpm)
    delay_ms = int(bar_ms * 0.5)
    available = {l.instrument_id for l in ctx.state.get("arrangement").layers} if ctx.state.get("arrangement") else set()
    schedule = ctx.state.get("arrangement").layer_schedule if ctx.state.get("arrangement") else None

    events: list[RhythmEvent] = []
    for e in melody.events:
        if e.type != "note":
            continue
        events.append(RhythmEvent(
            t=e.t + delay_ms,
            type="note",
            pitch=e.pitch,
            duration_ms=int(e.duration_ms * 0.85),
            velocity=max(28, int(e.velocity * 0.6)),
            beat_index=e.beat_index,
            section=e.section,
        ))

    events = filter_events_by_schedule(
        events, "echo_synth", schedule, ctx.bpm, available,
    )
    if not events:
        return None

    return Track(
        id="echo_synth",
        instrument_id="echo_synth",
        instrument="Echo Synth",
        midi_channel=5,
        role="lead",
        events=events,
    )


register(InstrumentDefinition(
    instrument_id="echo_synth",
    display_name="Echo Synth",
    role="lead",
    midi_channel=5,
    requires_llm=False,
    compose=_compose_echo_synth,
))
