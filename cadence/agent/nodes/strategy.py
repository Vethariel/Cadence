"""Nodo determinista: selección de estrategias desde generation_seed."""

from cadence.schemas.song_state import SongState
from cadence.music.strategy_pools import compute_generation_seed, select_strategies
from cadence.music.style_profile import effective_genre_tags


def strategy_planner_node(state: SongState) -> dict:
    """
    Calcula generation_seed y elige arp/harmony/paleta desde pools.
    drum/bass se sobrescriben en instrument_planner (elección del agente).
    """
    intent = state["intent"]
    structure = state["structure"]
    proposal = state.get("technical_proposal")

    seed = state.get("generation_seed") or compute_generation_seed(
        intent.raw_prompt,
        structure.total_bars,
    )
    mode = proposal.mode if proposal else "minor"
    genre_tags = effective_genre_tags(state)
    energy = proposal.energy_level if proposal else 3

    strategies = select_strategies(
        seed, genre_tags, mode, intent.use_case, energy,
    )

    return {"generation_seed": seed, "strategies": strategies}
