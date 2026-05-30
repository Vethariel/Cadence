"""Tests del pipeline determinista (sin LLM)."""

from cadence.music.narrative_contract import build_narrative_contract
from cadence.music.narrative_templates import build_narrative_from_template
from cadence.music.prompt_resolve import (
    genres_from_prompt,
    has_explicit_technical_params,
    resolve_intent_from_prompt,
    resolve_use_case,
)
from cadence.music.structure_deterministic import build_structure_deterministic
from cadence.schemas.song_state import CreativeBrief, TechnicalProposal, UserIntent
from cadence.music.prompt_resolve import resolve_intent_from_prompt


def test_genres_from_boss_prompt():
    tags = genres_from_prompt("boss fight techno dubstep oscuro")
    assert "boss fight" in tags or "techno" in tags
    print("✓ test_genres_from_boss_prompt OK")


def test_technical_detection():
    assert has_explicit_technical_params("D minor 140 BPM 4/4")
    assert not has_explicit_technical_params("canción oscura para jefe")
    print("✓ test_technical_detection OK")


def test_use_case_loop():
    assert resolve_use_case("música de overworld en loop") == "loop"
    print("✓ test_use_case_loop OK")


def test_intent_uses_creative_brief():
    brief = CreativeBrief(
        logline="Final confrontation in the reactor core",
        dramatic_objective="Signal imminent boss phase",
        emotional_arc="dread → defiance → triumph",
        scene_and_context="Hero faces the corrupted AI",
        listener_journey="Tension mounts then releases on victory",
        mood_keywords=["dark", "urgent", "triumphant"],
        use_case="game",
        style_hints=["boss fight", "techno"],
        enriched_prompt="Dark techno boss fight with rising dread and heroic release.",
        reasoning="test",
    )
    intent = resolve_intent_from_prompt(
        "música para jefe",
        creative_brief=brief,
        llm_style_tags=["techno"],
    )
    assert intent.use_case == "game"
    assert intent.mood == "dark"
    assert "techno" in [t.lower() for t in intent.style_tags]
    print("✓ test_intent_uses_creative_brief OK")


def test_narrative_matches_structure():
    intent = resolve_intent_from_prompt("boss fight dark")
    proposal = TechnicalProposal(
        bpm=140,
        key="F",
        mode="minor",
        genre_tags=["techno", "boss fight"],
        energy_level=5,
        structure=["intro", "build-up", "drop", "outro"],
        reasoning="test",
    )
    narrative = build_narrative_from_template(proposal, intent, generation_seed=42)
    assert len(narrative.sections) == 4
    assert narrative.sections[2].narrative_role == "climax"
    contract = build_narrative_contract(narrative, intent)
    structure = build_structure_deterministic(
        proposal, narrative, intent, narrative_contract=contract,
    )
    assert structure.sections == contract.section_ids
    assert structure.total_bars > 0
    print("✓ test_narrative_matches_structure OK")


if __name__ == "__main__":
    test_genres_from_boss_prompt()
    test_technical_detection()
    test_use_case_loop()
    test_intent_uses_creative_brief()
    test_narrative_matches_structure()
