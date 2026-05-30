"""Guion narrativo determinista."""

from cadence.music.narrative_templates import build_narrative_from_template
from cadence.schemas.song_state import SongState


def narrative_deterministic_node(state: SongState) -> dict:
    intent = state["intent"]
    proposal = state["technical_proposal"]
    if not proposal:
        raise ValueError("narrative_deterministic requiere technical_proposal")

    seed = state.get("generation_seed", 0)
    narrative = build_narrative_from_template(
        proposal,
        intent,
        generation_seed=seed,
        creative_brief=state.get("creative_brief"),
    )
    return {"narrative": narrative}
