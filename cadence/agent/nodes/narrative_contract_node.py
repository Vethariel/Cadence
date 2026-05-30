"""Congela el guion narrativo como contrato inmutable por solicitud."""

from cadence.music.narrative_contract import build_narrative_contract
from cadence.schemas.song_state import SongState


def narrative_contract_node(state: SongState) -> dict:
    """
    Genera narrative_contract justo después de narrative_planner.
    Source of truth intra-request para section_ids, arc_type, global_motif y firma del prompt.
    """
    narrative = state.get("narrative")
    intent = state["intent"]
    if not narrative:
        raise ValueError("narrative_contract_node requiere narrative en el estado")

    contract = build_narrative_contract(narrative, intent)
    return {"narrative_contract": contract}
