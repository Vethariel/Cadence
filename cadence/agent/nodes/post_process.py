"""Post-procesado expresivo: crescendo + humanize."""

from cadence.agent.nodes.narrative_apply import section_intent_map
from cadence.music.crescendo import apply_crescendo
from cadence.music.humanize import humanize_tracks
from cadence.music.melody_post import apply_melody_post
from cadence.schemas.song_state import SongState


def post_process_node(state: SongState) -> dict:
    """
    Aplica post-proceso melódico, crescendo narrativo y humanización.
    Se ejecuta tras compose_orchestra y antes del validator.
    """
    tracks = state.get("tracks", [])
    if not tracks:
        return {}

    structure = state["structure"]
    proposal = state.get("technical_proposal")
    bpm = proposal.bpm if proposal else 120
    narrative = state.get("narrative")
    development = state.get("development")
    seed = (
        development.generation_seed
        if development
        else state.get("generation_seed", 0)
    )

    tracks = apply_melody_post(tracks, state)
    tracks = apply_crescendo(
        tracks,
        structure,
        bpm,
        section_intent_map(narrative),
    )
    tracks = humanize_tracks(tracks, seed)

    return {"tracks": tracks}
