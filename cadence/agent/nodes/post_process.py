"""Post-procesado expresivo: melodía, timbres, crescendo, humanize."""

from cadence.agent.nodes.narrative_apply import section_intent_map
from cadence.music.crescendo import apply_crescendo
from cadence.music.humanize import humanize_tracks
from cadence.music.instrument_catalog import (
    apply_orchestration_gm,
    orchestration_for_state,
)
from cadence.music.melody_post import apply_melody_post
from cadence.schemas.song_state import SongState


def post_process_node(state: SongState) -> dict:
    """
    Pipeline post-orquesta:
    1. Melodía (silencios/densidad según estilo y energía)
    2. Timbres GM (orchestration_plan del agente o fallback)
    3. Crescendo + humanize
    """
    tracks = state.get("tracks", [])
    if not tracks:
        return {}

    structure = state["structure"]
    proposal = state.get("technical_proposal")
    narrative = state.get("narrative")
    development = state.get("development")
    bpm = proposal.bpm if proposal else 120
    seed = (
        development.generation_seed
        if development
        else state.get("generation_seed", 0)
    )

    tracks = apply_melody_post(tracks, state)
    plan = orchestration_for_state(state, tracks)
    tracks = apply_orchestration_gm(tracks, plan)
    tracks = apply_crescendo(
        tracks,
        structure,
        bpm,
        section_intent_map(narrative),
    )
    tracks = humanize_tracks(tracks, seed)

    return {"tracks": tracks}
