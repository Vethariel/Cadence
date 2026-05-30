"""Nodo determinista: genera HarmonyPlan compartido por bajo, melodía y pad."""

from cadence.schemas.song_state import SongState
from cadence.music.harmony_theory import build_harmony_plan
from cadence.music.narrative_contract import contract_section_intent_map


def harmony_planner_node(state: SongState) -> dict:
    """
    Define la progresión de acordes por sección a partir de
    key/mode, estructura y guion narrativo (harmonic_tension, role).
    """
    proposal = state.get("technical_proposal")
    structure = state["structure"]
    narrative = state.get("narrative")

    if proposal:
        key = proposal.key
        mode = proposal.mode
    else:
        key = "C"
        mode = "minor"

    contract = state.get("narrative_contract")
    intent_map = contract_section_intent_map(
        narrative, contract, context="harmony_planner", state=state,
    )

    intent = state["intent"]
    section_ids = list(contract.section_ids) if contract else list(structure.sections)
    harmony = build_harmony_plan(
        sections=section_ids,
        key=key,
        mode=mode,
        narrative_sections=intent_map,
        harmony_pool=state.get("strategies").harmony_pool if state.get("strategies") else None,
        use_case=intent.use_case,
        cadence_plan=proposal.cadence_plan if proposal else None,
    )

    return {"harmony": harmony}
