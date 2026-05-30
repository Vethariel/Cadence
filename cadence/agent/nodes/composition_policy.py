"""Anclas narrativas, límites creativos y subsemillas — tras align_sections."""

from cadence.music.narrative_anchors import build_narrative_anchors
from cadence.music.seed_policy import build_node_seeds
from cadence.music.strategy_pools import compute_generation_seed
from cadence.schemas.song_state import SongState


def composition_policy_node(state: SongState) -> dict:
    """
    Fija por solicitud:
    - generation_seed + node_seeds (aleatoriedad controlada)
    - narrative_anchors (baja variación)
    creative_variation y composition_archetype se fijan en strategy_planner.
    """
    intent = state["intent"]
    narrative = state.get("narrative")
    contract = state.get("narrative_contract")
    structure = state.get("structure")
    proposal = state.get("technical_proposal")

    if not narrative or not contract or not structure:
        raise ValueError(
            "composition_policy requiere narrative, narrative_contract y structure",
        )

    generation_seed = state.get("generation_seed") or compute_generation_seed(
        intent.raw_prompt,
        structure.total_bars,
    )
    anchors = build_narrative_anchors(narrative, contract)
    node_seeds = build_node_seeds(generation_seed)

    return {
        "generation_seed": generation_seed,
        "node_seeds": node_seeds,
        "narrative_anchors": anchors,
    }
