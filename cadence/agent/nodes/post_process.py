"""Post-procesado expresivo: melodía, timbres, crescendo, humanize."""

from cadence.agent.nodes.narrative_apply import section_intent_map
from cadence.music.crescendo import apply_crescendo
from cadence.music.humanize import humanize_tracks
from cadence.music.repair_dynamics import (
    apply_repair_dynamic_range,
    apply_repair_intensity_arc,
)
from cadence.music.narrative_contract import contract_section_intent_map
from cadence.music.instrument_catalog import (
    apply_orchestration_gm,
    orchestration_for_state,
)
from cadence.music.melody_post import apply_melody_post
from cadence.music.seed_policy import seed_for_state
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
    time_signature = list(proposal.time_signature) if proposal else [4, 4]
    seed = seed_for_state(state, "humanize") or (
        development.generation_seed
        if development
        else state.get("generation_seed", 0)
    )

    tracks = apply_melody_post(tracks, state)
    plan = orchestration_for_state(state, tracks)
    tracks = apply_orchestration_gm(tracks, plan, state=state)
    intent_map = contract_section_intent_map(
        narrative, state.get("narrative_contract"), context="post_process", state=state,
    )
    tracks = apply_crescendo(tracks, structure, bpm, intent_map, time_signature)

    repair_actions = state.get("repair_actions") or []
    if "recalc_dynamic_range" in repair_actions:
        tracks = apply_repair_dynamic_range(
            tracks, structure, bpm, intent_map, time_signature=time_signature,
        )
    if "adjust_section_intensity" in repair_actions:
        tracks = apply_repair_intensity_arc(tracks, structure, bpm, intent_map)

    tracks = humanize_tracks(tracks, seed)

    return {
        "tracks": tracks,
        "repair_actions": None,
        "repair_layers": None,
    }
