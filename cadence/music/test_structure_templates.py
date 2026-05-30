"""Tests de plantillas de estructura por use_case."""

from cadence.music.structure_templates import (
    default_structure_for_use_case,
    extract_explicit_structure_from_prompt,
    is_generic_pop_structure,
    prompt_requests_specific_form,
    resolve_proposal_structure,
)
from cadence.schemas.song_state import TechnicalProposal, UserIntent


def test_default_loop_not_pop():
    ids = default_structure_for_use_case(
        "loop",
        "Loop de exploración overworld: ambiente calmado, pads y drones",
    )
    assert ids != ["intro", "verse", "chorus", "outro"]
    assert "pad_layering" in ids or "melodic_motif" in ids


def test_default_boss_platform_not_pop():
    ids = default_structure_for_use_case(
        "game",
        "Pelea de jefe en plataforma: orquestación compacta, pocos instrumentos",
    )
    assert "build-up" in ids or "drop" in ids
    assert ids != ["intro", "verse", "chorus", "outro"]


def test_extract_explicit_structure():
    ids = extract_explicit_structure_from_prompt(
        "estructura intro-verse-chorus-outro en D minor",
    )
    assert ids == ["intro", "verse", "chorus", "outro"]


def test_resolve_replaces_generic_pop():
    intent = UserIntent(
        raw_prompt="Loop overworld ambiente",
        knowledge_level="non_technical",
        use_case="loop",
    )
    proposal = TechnicalProposal(
        bpm=75,
        key="C",
        mode="minor",
        genre_tags=["ambient"],
        energy_level=1,
        structure=["intro", "verse", "chorus", "outro"],
        reasoning="test",
    )
    out = resolve_proposal_structure(proposal, intent)
    assert not is_generic_pop_structure(out.structure)
    assert prompt_requests_specific_form(intent.raw_prompt)


if __name__ == "__main__":
    test_default_loop_not_pop()
    test_default_boss_platform_not_pop()
    test_extract_explicit_structure()
    test_resolve_replaces_generic_pop()
    print("All structure_templates tests passed.")
