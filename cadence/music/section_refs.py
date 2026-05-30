"""
Referencias de sección canónicas — IDs alineados al narrative_contract.
"""

from __future__ import annotations

from cadence.schemas.song_state import SongState


def canonical_section_ids(state: SongState | dict) -> list[str]:
    """IDs de sección en orden dramático (post align_sections)."""
    contract = state.get("narrative_contract") if isinstance(state, dict) else None
    structure = state.get("structure") if isinstance(state, dict) else None
    if contract is not None:
        return list(contract.section_ids)
    if structure is not None:
        return list(structure.sections)
    return []


def format_section_ids_for_llm(
    state: SongState | dict,
    *,
    include_instruction: bool = True,
) -> str:
    """Bloque de prompt: usa exactamente estos section IDs."""
    ids = canonical_section_ids(state)
    if not ids:
        return "(sin secciones canónicas en el estado)"
    lines = [
        "=== SECTION IDs (CANÓNICOS) ===",
        f"Orden fijo: {', '.join(ids)}",
    ]
    if include_instruction:
        lines.append(
            "Usa EXACTAMENTE estos section IDs en frases, eventos y capas activas. "
            "No renombres, no omitas ni inventes secciones distintas."
        )
    return "\n".join(lines)
