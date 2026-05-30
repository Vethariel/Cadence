"""Reconcilia structure_planner con narrative_contract — IDs canónicos."""

from cadence.music.narrative_contract import (
    SectionAlignmentError,
    align_structure_to_contract,
    assert_sections_match_contract,
)
from cadence.schemas.song_state import SongState


def align_sections_node(state: SongState) -> dict:
    """
    Mapea structure.sections ↔ narrative_contract.section_ids,
    normaliza IDs canónicos y falla temprano si el mapeo no es confiable.
    """
    structure = state.get("structure")
    narrative = state.get("narrative")
    contract = state.get("narrative_contract")

    if not structure or not narrative or not contract:
        raise ValueError(
            "align_sections requiere structure, narrative y narrative_contract",
        )

    try:
        aligned_structure, aligned_narrative, alignment = align_structure_to_contract(
            structure, narrative, contract,
        )
    except SectionAlignmentError as exc:
        raise ValueError(f"align_sections: {exc}") from exc

    assert_sections_match_contract(
        aligned_structure, contract, context="align_sections",
    )

    from cadence.observability.pipeline_log import log_section_reconciliation

    trace_update = log_section_reconciliation(
        state,
        planner_section_ids=list(alignment.planner_section_ids),
        canonical_section_ids=list(contract.section_ids),
        mapping=dict(alignment.mapping),
        method=alignment.method,
        realigned=alignment.realigned,
    )

    return {
        "structure": aligned_structure,
        "narrative": aligned_narrative,
        "section_alignment": alignment,
        **trace_update,
    }
