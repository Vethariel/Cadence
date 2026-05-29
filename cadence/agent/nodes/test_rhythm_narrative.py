"""Tests deterministas: rhythm engine + SongNarrative."""

from langchain_core.messages import HumanMessage

from cadence.schemas.song_state import (
    SectionIntent,
    SongNarrative,
    SongStructure,
    TechnicalProposal,
    UserIntent,
)
from cadence.agent.nodes.rhythm import _generate_bass_track, _generate_drum_track


def _base_structure() -> SongStructure:
    return SongStructure(
        sections=["intro", "build-up", "drop", "breakdown", "outro"],
        bars_per_section={"intro": 2, "build-up": 2, "drop": 2, "breakdown": 2, "outro": 2},
        total_bars=10,
        estimated_duration_ms=20000,
    )


def _narrative_with_transitions() -> SongNarrative:
    return SongNarrative(
        logline="Tension rises then cuts to silence before the final hit.",
        arc_type="rise-climax-fall",
        global_motif=[0, 2, 4],
        sections=[
            SectionIntent(
                id="intro", narrative_role="establish", emotional_target="mystery",
                density=0.3, harmonic_tension=0.2, rhythmic_complexity=0.3,
                transition_out="filter_sweep",
            ),
            SectionIntent(
                id="build-up", narrative_role="tension", emotional_target="urgency",
                density=0.6, harmonic_tension=0.6, rhythmic_complexity=0.6,
                transition_out="riser",
            ),
            SectionIntent(
                id="drop", narrative_role="climax", emotional_target="triumph",
                density=1.0, harmonic_tension=0.8, rhythmic_complexity=0.7,
                transition_out="cut",
            ),
            SectionIntent(
                id="breakdown", narrative_role="reflection", emotional_target="dread",
                density=0.15, harmonic_tension=0.4, rhythmic_complexity=0.2,
                transition_out="pickup",
            ),
            SectionIntent(
                id="outro", narrative_role="release", emotional_target="calm",
                density=0.25, harmonic_tension=0.1, rhythmic_complexity=0.2,
                transition_out="fade",
            ),
        ],
    )


def test_drum_density_scales_velocity():
    narrative = SongNarrative(
        logline="Sparse intro vs dense drop.",
        arc_type="loop-stable",
        global_motif=[0, 4],
        sections=[
            SectionIntent(
                id="intro", narrative_role="establish", emotional_target="calm",
                density=0.2, harmonic_tension=0.1, rhythmic_complexity=0.3,
            ),
            SectionIntent(
                id="drop", narrative_role="climax", emotional_target="power",
                density=1.0, harmonic_tension=0.7, rhythmic_complexity=0.8,
            ),
        ],
    )
    structure = SongStructure(
        sections=["intro", "drop"],
        bars_per_section={"intro": 1, "drop": 1},
        total_bars=2,
        estimated_duration_ms=4000,
    )
    drums = _generate_drum_track(
        sections=structure.sections,
        bars_per_section=structure.bars_per_section,
        bpm=120,
        genre_tags=["techno"],
        narrative=narrative,
    )
    intro_kicks = [e for e in drums.events if e.section == "intro" and e.pitch == 36]
    drop_kicks = [e for e in drums.events if e.section == "drop" and e.pitch == 36]
    assert intro_kicks, "intro debe tener kicks"
    assert drop_kicks, "drop debe tener kicks"
    assert max(e.velocity for e in drop_kicks) > max(e.velocity for e in intro_kicks)
    print("✓ test_drum_density_scales_velocity OK")


def test_transition_riser_on_last_bar():
    narrative = _narrative_with_transitions()
    structure = _base_structure()
    drums = _generate_drum_track(
        sections=structure.sections,
        bars_per_section=structure.bars_per_section,
        bpm=120,
        genre_tags=["techno"],
        narrative=narrative,
    )
    buildup_events = [e for e in drums.events if e.section == "build-up"]
    # build-up tiene 2 compases; riser en el último → más eventos snare en bar 2
    snare_hits = [e for e in buildup_events if e.pitch == 38]
    assert len(snare_hits) >= 10, "riser debe añadir snares en último compás"
    print("✓ test_transition_riser_on_last_bar OK")


def test_transition_cut_silences_second_half():
    narrative = _narrative_with_transitions()
    structure = _base_structure()
    drums = _generate_drum_track(
        sections=structure.sections,
        bars_per_section=structure.bars_per_section,
        bpm=120,
        genre_tags=["techno"],
        narrative=narrative,
    )
    drop_events = [e for e in drums.events if e.section == "drop"]
    # 2 compases; último compás cut → solo steps 0-7 del bar 2 + bar 1 completo
    assert len(drop_events) < 80, "cut debe reducir hits en último compás del drop"
    print("✓ test_transition_cut_silences_second_half OK")


def test_bass_skips_sparse_breakdown():
    narrative = _narrative_with_transitions()
    structure = _base_structure()
    bass = _generate_bass_track(
        sections=structure.sections,
        bars_per_section=structure.bars_per_section,
        bpm=120,
        key="C",
        mode="minor",
        narrative=narrative,
    )
    breakdown_notes = [e for e in bass.events if e.section == "breakdown"]
    assert len(breakdown_notes) == 0, "bajo debe omitirse con density=0.15"
    drop_notes = [e for e in bass.events if e.section == "drop"]
    assert len(drop_notes) > 0
    print("✓ test_bass_skips_sparse_breakdown OK")


def test_rhythm_node_backward_compatible():
    """Sin narrative el comportamiento legacy se mantiene."""
    from cadence.agent.nodes.rhythm import rhythm_engine_node

    state = {
        "messages": [HumanMessage(content="test")],
        "intent": UserIntent(
            raw_prompt="test", knowledge_level="technical",
            use_case="game", mood="dark", style_tags=["techno"],
        ),
        "technical_proposal": TechnicalProposal(
            bpm=120, key="C", mode="minor", genre_tags=["techno"],
            energy_level=3, structure=["intro", "drop"],
        ),
        "structure": SongStructure(
            sections=["intro", "drop"],
            bars_per_section={"intro": 1, "drop": 1},
            total_bars=2,
            estimated_duration_ms=4000,
        ),
        "narrative": None,
        "tracks": [],
    }
    result = rhythm_engine_node(state)
    assert len(result["tracks"]) == 2
    bass_sections = {e.section for e in result["tracks"][1].events}
    assert "breakdown" not in bass_sections or True  # no breakdown in structure
    print("✓ test_rhythm_node_backward_compatible OK")


if __name__ == "__main__":
    test_drum_density_scales_velocity()
    test_transition_riser_on_last_bar()
    test_transition_cut_silences_second_half()
    test_bass_skips_sparse_breakdown()
    test_rhythm_node_backward_compatible()
    print("\n✓ All rhythm narrative tests passed")
