from cadence.agent.nodes.melody import compose_melody_track
from cadence.instruments.context import ComposeContext
from cadence.instruments.registry import InstrumentDefinition, register
from cadence.schemas.song_state import Track


def _compose_melody(ctx: ComposeContext) -> Track:
    track = compose_melody_track(ctx.state)
    return track.model_copy(update={"instrument_id": "melody"})


register(InstrumentDefinition(
    instrument_id="melody",
    display_name="Melody",
    role="lead",
    midi_channel=0,
    requires_llm=False,
    compose=_compose_melody,
))
