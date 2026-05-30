"""Tests del catálogo de formas y resolución de estructura."""

from cadence.music.structure_catalog import (
    STRUCTURE_FORMS,
    default_structure_for_use_case,
    expand_form,
    extract_explicit_structure_from_prompt,
    format_structure_catalog_for_llm,
    is_generic_pop_structure,
    is_valid_form_id,
    prompt_requests_specific_form,
    resolve_bars_per_section,
    resolve_proposal_structure,
    score_form,
    structure_from_brief,
    suggest_forms,
    validate_section_list,
)
from cadence.music.structure_forms_data import STRUCTURE_FORM_CATEGORIES
from cadence.schemas.song_state import CreativeBrief, TechnicalProposal, UserIntent


def test_expand_boss_edm():
    ids = expand_form("boss_edm")
    assert ids == ["intro", "build-up", "drop", "outro"]
    print("✓ test_expand_boss_edm OK")


def test_suggest_loop_ambient():
    forms = suggest_forms(use_case="loop", genre_tags=["ambient"], energy_level=2)
    assert forms[0] == "loop_ambient"
    print("✓ test_suggest_loop_ambient OK")


def test_structure_from_brief_arc():
    brief = CreativeBrief(
        logline="Overworld calm",
        dramatic_objective="exploration",
        emotional_arc="loop-stable calm layers",
        scene_and_context="field",
        listener_journey="peace",
        mood_keywords=["calm"],
        use_case="loop",
        style_hints=["ambient"],
        enriched_prompt="ambient loop",
        reasoning="t",
    )
    sections, fid = structure_from_brief(brief, genre_tags=["ambient"], energy_level=2)
    assert fid == "loop_ambient"
    assert "pad_layering" in sections
    print("✓ test_structure_from_brief_arc OK")


def test_resolve_uses_structure_form():
    intent = UserIntent(
        raw_prompt="boss fight techno",
        knowledge_level="non_technical",
        use_case="game",
        mood="dark",
        style_tags=["techno"],
    )
    proposal = TechnicalProposal(
        bpm=140,
        key="F",
        mode="minor",
        genre_tags=["techno", "boss fight"],
        energy_level=5,
        structure_form="boss_edm",
        structure=[],
        reasoning="test",
    )
    out = resolve_proposal_structure(proposal, intent)
    assert out.structure == expand_form("boss_edm")
    assert out.structure_form == "boss_edm"
    print("✓ test_resolve_uses_structure_form OK")


def test_resolve_bars_from_form_and_target():
    proposal = TechnicalProposal(
        bpm=120,
        key="C",
        mode="minor",
        genre_tags=["techno"],
        energy_level=4,
        structure_form="boss_edm",
        structure=["intro", "build-up", "drop", "outro"],
        target_total_bars=48,
        reasoning="t",
    )
    bars = resolve_bars_per_section(proposal.structure, proposal)
    assert sum(bars.values()) == 48
    assert all(2 <= v <= 32 for v in bars.values())
    print("✓ test_resolve_bars_from_form_and_target OK")


def test_validate_section_list_rejects_short():
    assert validate_section_list(["intro"]) == []
    assert len(validate_section_list(["intro", "drop"])) == 2
    print("✓ test_validate_section_list_rejects_short OK")


def test_catalog_has_many_forms():
    assert len(STRUCTURE_FORMS) >= 40
    categorized = {fid for ids in STRUCTURE_FORM_CATEGORIES.values() for fid in ids}
    assert categorized == set(STRUCTURE_FORMS.keys())
    text = format_structure_catalog_for_llm(suggested=["boss_edm"])
    assert "boss_dnb" in text
    assert "loop_ambient" in text
    assert "★ Sugeridas" in text
    print("✓ test_catalog_has_many_forms OK")


def test_suggest_menu_theme():
    forms = suggest_forms(use_case="loop", genre_tags=["menu", "ui"], energy_level=2)
    assert "menu_theme" in forms[:5]
    print("✓ test_suggest_menu_theme OK")


def test_expand_edm_double_drop_unique_sections():
    ids = expand_form("edm_double_drop")
    assert len(ids) == len(set(ids))
    assert "drop" in ids and "climax" in ids
    print("✓ test_expand_edm_double_drop_unique_sections OK")


def test_score_form_boss_orchestral():
    s = score_form(
        "boss_orchestral",
        use_case="game",
        genre_tags=["orchestral", "epic"],
        energy_level=5,
    )
    assert s > score_form("loop_ambient", use_case="game", genre_tags=["orchestral"], energy_level=5)
    print("✓ test_score_form_boss_orchestral OK")


def test_default_loop_from_exploration_prompt():
    ids = default_structure_for_use_case(
        "loop",
        "Loop de exploración overworld: ambiente calmado, pads y drones",
    )
    assert not is_generic_pop_structure(ids)
    assert "pad_layering" in ids or "melodic_motif" in ids or "exploration_bed" in ids


def test_extract_explicit_structure_from_prompt():
    ids = extract_explicit_structure_from_prompt(
        "estructura intro-verse-chorus-outro en D minor",
    )
    assert ids == ["intro", "verse", "chorus", "outro"]


if __name__ == "__main__":
    test_expand_boss_edm()
    test_suggest_loop_ambient()
    test_structure_from_brief_arc()
    test_resolve_uses_structure_form()
    test_resolve_bars_from_form_and_target()
    test_validate_section_list_rejects_short()
    test_catalog_has_many_forms()
    test_suggest_menu_theme()
    test_expand_edm_double_drop_unique_sections()
    test_score_form_boss_orchestral()
    test_default_loop_from_exploration_prompt()
    test_extract_explicit_structure_from_prompt()
    print("\nAll structure_catalog tests passed.")
