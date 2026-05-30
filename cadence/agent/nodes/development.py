"""Nodo determinista: DevelopmentPlan — evolución motivica por sección."""

from cadence.schemas.song_state import SongState
from cadence.music.development_theory import build_development_plan
from cadence.music.style_archetype import get_composition_archetype
from cadence.music.narrative_contract import contract_section_intent_map


def development_planner_node(state: SongState) -> dict:
    """
    Define cómo evoluciona el motivo global en cada sección
    según narrative_role, density y seed de generación.
    """
    narrative = state.get("narrative")
    structure = state["structure"]
    seed = state.get("generation_seed", 0)

    contract = state.get("narrative_contract")
    global_motif = (
        list(contract.global_motif)
        if contract
        else (list(narrative.global_motif) if narrative else [])
    )

    proposal = state.get("technical_proposal")
    energy = proposal.energy_level if proposal else 3
    intent = state["intent"]

    archetype = get_composition_archetype(state)
    section_ids = (
        list(contract.section_ids) if contract else list(structure.sections)
    )
    intent_map = contract_section_intent_map(
        narrative, contract, context="development_planner", state=state,
    )
    development = build_development_plan(
        sections=section_ids,
        global_motif=global_motif,
        narrative_sections=intent_map,
        generation_seed=seed,
        energy_level=energy,
        bars_per_section=structure.bars_per_section,
        use_case=intent.use_case,
        composition_archetype=archetype,
    )

    out: dict = {"development": development}
    harmony = state.get("harmony")
    if harmony:
        from cadence.music.segment_variation import enrich_harmony_with_segments

        strategies = state.get("strategies")
        pool = strategies.harmony_pool if strategies else None
        out["harmony"] = enrich_harmony_with_segments(
            harmony,
            development,
            intent_map,
            seed=seed,
            harmony_pool=pool,
        )
    return out
