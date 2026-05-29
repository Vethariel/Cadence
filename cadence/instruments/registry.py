"""Registro extensible de instrumentos compositores."""

from dataclasses import dataclass
from typing import Callable

from cadence.schemas.song_state import Track
from cadence.instruments.context import ComposeContext

ComposeFn = Callable[[ComposeContext], Track | None]


@dataclass
class InstrumentDefinition:
    instrument_id: str
    display_name: str
    role: str
    midi_channel: int
    requires_llm: bool
    compose: ComposeFn


_REGISTRY: dict[str, InstrumentDefinition] = {}


def register(defn: InstrumentDefinition) -> InstrumentDefinition:
    _REGISTRY[defn.instrument_id] = defn
    return defn


def get_instrument(instrument_id: str) -> InstrumentDefinition:
    if instrument_id not in _REGISTRY:
        raise KeyError(f"Instrumento no registrado: {instrument_id}")
    return _REGISTRY[instrument_id]


def list_instruments() -> list[str]:
    return list(_REGISTRY.keys())


def compose_layer(ctx: ComposeContext) -> Track | None:
    from cadence.music.layer_schedule import filter_events_by_schedule

    defn = get_instrument(ctx.layer.instrument_id)
    track = defn.compose(ctx)
    if track is None:
        return None
    if not track.instrument_id:
        track = track.model_copy(update={"instrument_id": defn.instrument_id})
    arrangement = ctx.state.get("arrangement")
    if arrangement and arrangement.layer_schedule and track.events:
        available = {l.instrument_id for l in arrangement.layers}
        filtered = filter_events_by_schedule(
            track.events,
            track.instrument_id,
            arrangement.layer_schedule,
            ctx.bpm,
            available,
        )
        if not filtered:
            return None
        track = track.model_copy(update={"events": filtered})
    return track
