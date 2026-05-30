"""Nodo determinista: selección de estrategias desde generation_seed."""

from cadence.schemas.song_state import SongState
from cadence.music.seed_policy import derive_node_seed
from cadence.music.strategy_pools import compute_generation_seed, select_strategies
from cadence.music.creative_variation import build_creative_variation_bounds
from cadence.music.style_archetype import infer_composition_archetype
from cadence.music.style_profile import effective_genre_tags


def strategy_planner_node(state: SongState) -> dict:
    """
    Calcula generation_seed y elige arp/harmony/paleta desde pools.
    drum/bass se sobrescriben en instrument_planner (elección del agente).
    """
    intent = state["intent"]
    structure = state["structure"]
    proposal = state.get("technical_proposal")

    root_seed = state.get("generation_seed") or compute_generation_seed(
        intent.raw_prompt,
        structure.total_bars,
    )
    pool_seed = derive_node_seed(root_seed, "strategy_planner")
    mode = proposal.mode if proposal else "minor"
    genre_tags = effective_genre_tags(state)
    energy = proposal.energy_level if proposal else 3

    archetype = infer_composition_archetype(
        style_profile=state.get("style_profile"),
        raw_prompt=intent.raw_prompt,
        use_case=intent.use_case,
        energy_level=energy,
    )
    strategies = select_strategies(
        pool_seed or root_seed, genre_tags, mode, intent.use_case, energy,
        composition_archetype=archetype,
    )

    out: dict = {
        "generation_seed": root_seed,
        "strategies": strategies,
        "composition_archetype": archetype,
    }
    anchors = state.get("narrative_anchors")
    if anchors:
        out["creative_variation"] = build_creative_variation_bounds(
            anchors,
            energy_level=energy,
            use_case=intent.use_case,
            composition_archetype=archetype,
            generation_seed=root_seed,
        )
    return out
