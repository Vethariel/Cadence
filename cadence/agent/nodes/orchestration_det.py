"""Orquestación: aplica technical_spec (LLM) y valida con teoría musical."""

from cadence.music.orchestration_plan import apply_plan_to_strategies
from cadence.music.orchestration_pick import pick_orchestration_plan
from cadence.schemas.song_state import SongState


def orchestration_deterministic_node(state: SongState) -> dict:
    plan = pick_orchestration_plan(state)
    proposal = state["technical_proposal"]
    strategies = state.get("strategies")
    intent = state["intent"]

    return {
        "orchestration_plan": plan,
        "strategies": apply_plan_to_strategies(
            strategies,
            plan,
            energy_level=proposal.energy_level,
            use_case=intent.use_case,
        ),
    }
