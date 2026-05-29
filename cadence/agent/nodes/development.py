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
    genre_tags = proposal.genre_tags if proposal else None

    development = build_development_plan(
        sections=structure.sections,
        global_motif=global_motif,
        narrative_sections=section_intent_map(narrative),
        generation_seed=seed,
        genre_tags=genre_tags,
    )

    return {"development": development}
