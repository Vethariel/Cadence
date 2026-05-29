"""Eco determinista — melodía, arp o stabs según estrategia."""

from cadence.instruments.context import ComposeContext
from cadence.instruments.registry import InstrumentDefinition, register
from cadence.music.layer_schedule import filter_events_by_schedule, ms_per_bar
from cadence.schemas.song_state import RhythmEvent, Track

ECHO_SOURCES = ("auto", "melody", "arp_synth", "chord_stab")
_SOURCE_PRIORITY = ("melody", "arp_synth", "chord_stab")


def _resolve_echo_source_id(ctx: ComposeContext) -> str | None:
    strategies = ctx.state.get("strategies")
    preference = strategies.echo_source if strategies else "auto"
    if preference not in ECHO_SOURCES:
        preference = "auto"

    tracks = ctx.state.get("tracks", [])
    by_id = {t.id: t for t in tracks}

    if preference != "auto":
        src = by_id.get(preference)
        return preference if src and src.events else None

    for iid in _SOURCE_PRIORITY:
        src = by_id.get(iid)
        if src and src.events:
            return iid
    return None


def _compose_echo_synth(ctx: ComposeContext) -> Track | None:
    source_id = _resolve_echo_source_id(ctx)
    if not source_id:
        return None

    source = next(t for t in ctx.state.get("tracks", []) if t.id == source_id)
    if not source.events:
        return None

    bar_ms = ms_per_bar(ctx.bpm)
    delay_ms = int(bar_ms * 0.5)
    available = (
        {l.instrument_id for l in ctx.state.get("arrangement").layers}
        if ctx.state.get("arrangement")
        else set()
    )
    schedule = (
        ctx.state.get("arrangement").layer_schedule
        if ctx.state.get("arrangement")
        else None
    )

    vel_scale = 0.55 if source_id == "chord_stab" else 0.6

    events: list[RhythmEvent] = []
    for e in source.events:
        if e.type != "note":
            continue
        events.append(RhythmEvent(
            t=e.t + delay_ms,
            type="note",
            pitch=e.pitch,
            duration_ms=int(e.duration_ms * 0.85),
            velocity=max(28, int(e.velocity * vel_scale)),
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
