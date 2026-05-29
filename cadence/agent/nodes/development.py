"""Nodo determinista: DevelopmentPlan — evolución motivica por sección."""

from cadence.schemas.song_state import SongState
from cadence.music.development_theory import (
    build_development_plan,
    compute_generation_seed,
)
from cadence.agent.nodes.narrative_apply import section_intent_map


def development_planner_node(state: SongState) -> dict:
    """
    Define cómo evoluciona el motivo global en cada sección
    según narrative_role, density y seed de generación.
    """
    narrative = state.get("narrative")
    structure = state["structure"]
    intent = state["intent"]

    global_motif = list(narrative.global_motif) if narrative else []
    seed = state.get("generation_seed") or compute_generation_seed(
        intent.raw_prompt,
        structure.total_bars,
    )

    development = build_development_plan(
        sections=structure.sections,
        global_motif=global_motif,
        narrative_sections=section_intent_map(narrative),
        generation_seed=seed,
    )

    return {"development": development, "generation_seed": seed}
