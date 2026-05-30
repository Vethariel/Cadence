"""Tests del nodo align_sections y reconciliación con contrato."""

from cadence.agent.nodes.align_sections import align_sections_node
from cadence.music.narrative_contract import assert_sections_match_contract
from cadence.music.section_refs import canonical_section_ids
from cadence.test_fixtures.pipeline_coherence import (
    CANONICAL_SECTION_IDS,
    PLANNER_SECTION_IDS,
    build_aligned_pipeline_state,
    build_pre_align_state,
)


def test_align_sections_node_canonicalizes_planner_ids():
    state = build_pre_align_state()
    out = align_sections_node(state)
    assert out["structure"].sections == CANONICAL_SECTION_IDS
    assert out["narrative"].sections[0].id == "intro"
    assert out["section_alignment"].realigned is True
    assert out["section_alignment"].mapping["Intro"] == "intro"
    assert "pipeline_trace" in out
    recon = [e for e in out["pipeline_trace"] if e.get("event") == "section_reconciliation"]
    assert len(recon) == 1
    assert recon[0]["output_section_ids"] == CANONICAL_SECTION_IDS
    print("✓ test_align_sections_node_canonicalizes_planner_ids OK")


def test_align_sections_bars_remapped():
    out = align_sections_node(build_pre_align_state())
    bars = out["structure"].bars_per_section
    assert bars == {"intro": 4, "build-up": 8, "drop": 8, "outro": 4}
    assert out["structure"].total_bars == 24
    print("✓ test_align_sections_bars_remapped OK")


def test_aligned_state_matches_contract():
    state = build_aligned_pipeline_state(generation_seed=42)
    contract = state["narrative_contract"]
    assert_sections_match_contract(state["structure"], contract)
    assert canonical_section_ids(state) == contract.section_ids
    assert [s.id for s in state["narrative"].sections] == contract.section_ids
    print("✓ test_aligned_state_matches_contract OK")


def test_align_sections_requires_contract():
    state = build_pre_align_state()
    state.pop("narrative_contract")
    try:
        align_sections_node(state)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "narrative_contract" in str(exc)
    print("✓ test_align_sections_requires_contract OK")


if __name__ == "__main__":
    test_align_sections_node_canonicalizes_planner_ids()
    test_align_sections_bars_remapped()
    test_aligned_state_matches_contract()
    test_align_sections_requires_contract()
    print("\n✓ All align_sections tests passed")
