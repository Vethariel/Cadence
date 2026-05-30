"""Tests: technical_spec → merge determinista."""

from cadence.music.technical_proposal_apply import (
    merge_strategies_from_proposal,
    normalize_global_motif,
    normalize_technical_proposal_composition,
    snap_drum_pattern,
    snap_harmony_pool,
)
from cadence.schemas.song_state import GenerationStrategies, TechnicalProposal


def test_merge_strategies_from_proposal():
    base = GenerationStrategies(
        generation_seed=1,
        drum_pattern="default_a",
        bass_pattern="root_fifth_a",
        harmony_pool="classic",
    )
    proposal = TechnicalProposal(
        bpm=140,
        key="F",
        mode="minor",
        genre_tags=["techno"],
        energy_level=5,
        drum_pattern="techno",
        bass_pattern="driving",
        harmony_pool="game",
        arp_pattern="up_a",
        reasoning="t",
    )
    merged = merge_strategies_from_proposal(base, proposal)
    assert "techno" in merged.drum_pattern
    assert "driving" in merged.bass_pattern
    assert merged.harmony_pool == "game"
    assert merged.arp_pattern == "up_a"
    print("✓ test_merge_strategies_from_proposal OK")


def test_normalize_global_motif():
    assert normalize_global_motif([0, 2, 4, 2]) == [0, 2, 4, 2]
    assert normalize_global_motif([0, 1]) == []
    print("✓ test_normalize_global_motif OK")


def test_snap_drum_pattern():
    assert snap_drum_pattern("techno_a")
    assert snap_drum_pattern("dubstep")
    print("✓ test_snap_drum_pattern OK")


def test_snap_harmony_pool():
    assert snap_harmony_pool("cinematic") == "cinematic"
    assert snap_harmony_pool("invalid") == ""
    print("✓ test_snap_harmony_pool OK")


def test_normalize_technical_proposal_composition():
    proposal = TechnicalProposal(
        bpm=128,
        key="C",
        drum_pattern="techno",
        harmony_pool="cinematic",
        texture_mode="bedded",
        composition_archetype="compact_action",
        global_motif=[0, 2, 4],
        reasoning="t",
    )
    norm = normalize_technical_proposal_composition(proposal)
    assert "techno" in norm.drum_pattern
    assert norm.harmony_pool == "cinematic"
    assert norm.texture_mode == "bedded"
    assert norm.composition_archetype == "compact_action"
    assert norm.global_motif == [0, 2, 4]
    print("✓ test_normalize_technical_proposal_composition OK")


if __name__ == "__main__":
    test_merge_strategies_from_proposal()
    test_normalize_global_motif()
    test_snap_drum_pattern()
    test_snap_harmony_pool()
    test_normalize_technical_proposal_composition()
    print("\nAll technical_proposal_apply tests passed.")
