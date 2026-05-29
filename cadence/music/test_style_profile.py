"""Tests para helpers de MusicalStyleProfile."""

from cadence.music.style_profile import (
    effective_genre_tags,
    merge_proposal_genre_tags,
    programs_matching_avoid,
    sanitize_style_references,
)
from cadence.schemas.song_state import MusicalStyleProfile, TechnicalProposal, UserIntent


def test_programs_matching_avoid_calliope():
    bad = programs_matching_avoid(["calliope"])
    assert 82 in bad


def test_merge_proposal_genre_tags_prioritizes_profile():
    profile = MusicalStyleProfile(genres=["techno", "dubstep"])
    merged = merge_proposal_genre_tags(["chiptune", "arcade"], profile)
    assert merged[0] == "techno"
    assert "chiptune" in merged


def test_sanitize_style_references_drops_genres():
    refs = sanitize_style_references(
        ["techno", "dubstep", "boss fight", "Super Bomberman"],
        ["techno", "dubstep", "boss fight"],
    )
    assert refs == ["Super Bomberman"]


def test_sanitize_style_references_empty_when_only_genres():
    assert sanitize_style_references(
        ["techno", "dubstep", "boss fight"],
        ["techno", "dubstep", "boss fight", "combat"],
    ) == []


def test_effective_genre_tags_from_profile():
    state = {
        "style_profile": MusicalStyleProfile(
            genres=["techno", "dubstep"],
            references=["Super Bomberman"],
        ),
        "technical_proposal": TechnicalProposal(
            bpm=140,
            key="C",
            genre_tags=["chiptune"],
            energy_level=4,
        ),
        "intent": UserIntent(
            raw_prompt="test",
            knowledge_level="non_technical",
            style_tags=["arcade"],
        ),
    }
    tags = effective_genre_tags(state)
    assert tags[0] == "techno"
    assert "Super Bomberman" in tags
    assert "chiptune" in tags


if __name__ == "__main__":
    test_programs_matching_avoid_calliope()
    test_merge_proposal_genre_tags_prioritizes_profile()
    test_sanitize_style_references_drops_genres()
    test_sanitize_style_references_empty_when_only_genres()
    test_effective_genre_tags_from_profile()
    print("All style_profile tests passed.")
