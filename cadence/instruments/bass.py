from cadence.agent.nodes.rhythm import _generate_bass_track
from cadence.music.narrative_contract import section_intent_map_from_state
from cadence.instruments.context import ComposeContext
from cadence.instruments.registry import InstrumentDefinition, register
from cadence.schemas.song_state import Track


def _compose_bass(ctx: ComposeContext) -> Track:
    structure = ctx.state["structure"]
    strategies = ctx.state.get("strategies")
    track = _generate_bass_track(
        sections=structure.sections,
        bars_per_section=structure.bars_per_section,
        bpm=ctx.bpm,
        key=ctx.key,
        mode=ctx.mode,
        intent_map=section_intent_map_from_state(ctx.state, context="bass"),
        harmony=ctx.state.get("harmony"),
        bass_pattern_id=strategies.bass_pattern if strategies else None,
    )
    return track.model_copy(update={"instrument_id": "bass"})


register(InstrumentDefinition(
    instrument_id="bass",
    display_name="Bass Synth",
    role="bass",
    midi_channel=1,
    requires_llm=False,
    compose=_compose_bass,
))
