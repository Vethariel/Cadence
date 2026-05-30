"""Re-exporta API de estructura — implementación en structure_catalog."""

from cadence.music.structure_catalog import (
    GENERIC_POP_SECTIONS,
    default_structure_for_use_case,
    extract_explicit_structure_from_prompt,
    is_generic_pop_structure,
    prompt_lists_explicit_sections,
    prompt_requests_specific_form,
    resolve_proposal_structure,
)

__all__ = [
    "GENERIC_POP_SECTIONS",
    "default_structure_for_use_case",
    "extract_explicit_structure_from_prompt",
    "is_generic_pop_structure",
    "prompt_lists_explicit_sections",
    "prompt_requests_specific_form",
    "resolve_proposal_structure",
]
