from cadence.agent.nodes.pad import _generate_pad_track
from cadence.music.development_theory import section_development_map
from cadence.music.narrative_contract import section_intent_map_from_state
from cadence.instruments.context import ComposeContext
from cadence.instruments.registry import InstrumentDefinition, register
from cadence.schemas.song_state import Track


def _compose_pad(ctx: ComposeContext) -> Track | None:
    harmony = ctx.state.get("harmony")
    if not harmony:
        return None
    active = ctx.active_sections()
    if not active:
        return None

    structure = ctx.state["structure"]
    filtered_sections = [s for s in structure.sections if s in active]
    if not filtered_sections:
        return None

    development = ctx.state.get("development")
    track = _generate_pad_track(
        sections=structure.sections,
        bars_per_section=structure.bars_per_section,
        bpm=ctx.bpm,
        harmony=harmony,
        intent_map=section_intent_map_from_state(ctx.state, context="pad"),
        dev_map=section_development_map(development),
        time_signature=ctx.time_signature,
    )
    # Filtrar eventos a secciones activas
    events = [e for e in track.events if e.section in active]
    if not events:
        return None
    return track.model_copy(update={"events": events, "instrument_id": "pad"})


register(InstrumentDefinition(
    instrument_id="pad",
    display_name="Warm Pad",
    role="pad",
    midi_channel=2,
    requires_llm=False,
    compose=_compose_pad,
))
