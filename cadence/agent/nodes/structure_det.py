"""Macro-estructura determinista (compases por sección)."""

from cadence.music.structure_deterministic import build_structure_deterministic
from cadence.schemas.song_state import SongState


def structure_deterministic_node(state: SongState) -> dict:
    intent = state["intent"]
    proposal = state["technical_proposal"]
    narrative = state.get("narrative")
    contract = state.get("narrative_contract")

    if not proposal or not narrative:
        raise ValueError("structure_deterministic requiere proposal y narrative")

    structure = build_structure_deterministic(
        proposal, narrative, intent, narrative_contract=contract,
    )
    return {"structure": structure}
