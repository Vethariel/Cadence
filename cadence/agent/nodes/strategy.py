"""Nodo determinista: selección de estrategias desde generation_seed."""

from cadence.schemas.song_state import SongState
from cadence.music.strategy_pools import compute_generation_seed, select_strategies


def strategy_planner_node(state: SongState) -> dict:
    """
    Calcula generation_seed y elige drum/bass/harmony/arp
    desde pools deterministas antes de armonía y composición.
    """
    intent = state["intent"]
    structure = state["structure"]
    proposal = state.get("technical_proposal")

    seed = state.get("generation_seed") or compute_generation_seed(
        intent.raw_prompt,
        structure.total_bars,
    )
    mode = proposal.mode if proposal else "minor"
    genre_tags = proposal.genre_tags if proposal else intent.style_tags

    strategies = select_strategies(seed, genre_tags, mode)

    return {"generation_seed": seed, "strategies": strategies}
