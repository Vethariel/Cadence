from cadence.agent.nodes.rhythm import _generate_drum_track
from cadence.instruments.context import ComposeContext
from cadence.instruments.registry import InstrumentDefinition, register
from cadence.schemas.song_state import Track


def _compose_drums(ctx: ComposeContext) -> Track:
    structure = ctx.state["structure"]
    track = _generate_drum_track(
        sections=structure.sections,
        bars_per_section=structure.bars_per_section,
        bpm=ctx.bpm,
        genre_tags=ctx.genre_tags,
        narrative=ctx.state.get("narrative"),
    )
    return track.model_copy(update={"instrument_id": "drums"})


register(InstrumentDefinition(
    instrument_id="drums",
    display_name="Drum Kit",
    role="rhythm",
    midi_channel=9,
    requires_llm=False,
    compose=_compose_drums,
))
