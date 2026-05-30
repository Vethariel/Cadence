"""Nodo determinista: DevelopmentPlan — evolución motivica por sección."""

from cadence.schemas.song_state import SongState
from cadence.music.development_theory import build_development_plan
from cadence.agent.nodes.narrative_apply import section_intent_map


def development_planner_node(state: SongState) -> dict:
    """
    Define cómo evoluciona el motivo global en cada sección
    según narrative_role, density y seed de generación.
    """
    narrative = state.get("narrative")
    structure = state["structure"]
    seed = state.get("generation_seed", 0)

    global_motif = list(narrative.global_motif) if narrative else []

    proposal = state.get("technical_proposal")
    energy = proposal.energy_level if proposal else 3
    intent = state["intent"]

    development = build_development_plan(
        sections=structure.sections,
        global_motif=global_motif,
        narrative_sections=section_intent_map(narrative),
        generation_seed=seed,
        energy_level=energy,
        bars_per_section=structure.bars_per_section,
        use_case=intent.use_case,
    )

    return {"development": development}
