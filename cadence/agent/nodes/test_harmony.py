"""Tests deterministas de HarmonyPlan y pad."""

from langchain_core.messages import HumanMessage

from cadence.schemas.song_state import (
    SectionIntent,
    SongNarrative,
    SongStructure,
    TechnicalProposal,
    UserIntent,
)
from cadence.agent.nodes.harmony import harmony_planner_node
from cadence.agent.nodes.pad import _generate_pad_track, pad_composer_node
from cadence.agent.nodes.rhythm import _generate_bass_track
from cadence.music.harmony_theory import (
    build_harmony_plan,
    chord_at_bar,
    chord_pitches,
    harmony_summary_for_section,
)


def _mock_state():
    narrative = SongNarrative(
        logline="Boss fight arc",
        arc_type="rise-climax-fall",
        global_motif=[0, 2, 4],
        sections=[
            SectionIntent(
                id="intro", narrative_role="establish", emotional_target="mystery",
                density=0.3, harmonic_tension=0.2, rhythmic_complexity=0.3,
            ),
            SectionIntent(
                id="drop", narrative_role="climax", emotional_target="triumph",
                density=1.0, harmonic_tension=0.8, rhythmic_complexity=0.7,
            ),
            SectionIntent(
                id="breakdown", narrative_role="reflection", emotional_target="dread",
                density=0.15, harmonic_tension=0.3, rhythmic_complexity=0.2,
            ),
        ],
    )
    return {
        "messages": [HumanMessage(content="test")],
        "intent": UserIntent(
            raw_prompt="test", knowledge_level="non_technical",
            use_case="game", mood="dark", style_tags=["techno"],
        ),
        "technical_proposal": TechnicalProposal(
            bpm=120, key="F", mode="minor", genre_tags=["techno"],
            energy_level=5, structure=["intro", "drop", "breakdown"],
        ),
        "structure": SongStructure(
            sections=["intro", "drop", "breakdown"],
            bars_per_section={"intro": 4, "drop": 4, "breakdown": 4},
            total_bars=12,
            estimated_duration_ms=24000,
        ),
        "narrative": narrative,
        "tracks": [],
    }


def test_harmony_planner_node():
    result = harmony_planner_node(_mock_state())
    harmony = result["harmony"]
    assert harmony.key == "F"
    assert harmony.mode == "minor"
    assert len(harmony.sections) == 3
    drop_summary = harmony_summary_for_section(harmony, "drop")
    assert drop_summary != ""
    print(f"drop progression: {drop_summary}")
    print("✓ test_harmony_planner_node OK")


def test_bass_follows_chord_roots():
    state = _mock_state()
    harmony = harmony_planner_node(state)["harmony"]
    bass = _generate_bass_track(
        sections=state["structure"].sections,
        bars_per_section=state["structure"].bars_per_section,
        bpm=120,
        key="F",
        mode="minor",
        narrative=state["narrative"],
        harmony=harmony,
    )
    drop_notes = [e for e in bass.events if e.section == "drop"]
    assert len(drop_notes) > 0
    # Con armonía el bajo usa 4 notas por compás (root/fifth pattern)
    assert len(drop_notes) >= 16
    print("✓ test_bass_follows_chord_roots OK")


def test_pad_skips_sparse_breakdown():
    state = _mock_state()
    harmony = harmony_planner_node(state)["harmony"]
    pad = _generate_pad_track(
        sections=state["structure"].sections,
        bars_per_section=state["structure"].bars_per_section,
        bpm=120,
        harmony=harmony,
        narrative=state["narrative"],
    )
    breakdown_chords = [e for e in pad.events if e.section == "breakdown"]
    intro_chords = [e for e in pad.events if e.section == "intro"]
    assert len(breakdown_chords) == 0, "pad debe omitir breakdown sparse"
    assert len(intro_chords) > 0
    assert all(e.type == "chord" for e in pad.events)
    print("✓ test_pad_skips_sparse_breakdown OK")


def test_pad_composer_merges_tracks():
    state = _mock_state()
    state["harmony"] = harmony_planner_node(state)["harmony"]
    state["tracks"] = [
        type("T", (), {"id": "drums"})(),
        type("T", (), {"id": "bass"})(),
        type("T", (), {"id": "melody"})(),
    ]
    # Use proper Track objects - simpler approach
    from cadence.schemas.song_state import Track
    state["tracks"] = [
        Track(id="drums", instrument="Drums", role="rhythm"),
        Track(id="bass", instrument="Bass", role="bass"),
        Track(id="melody", instrument="Lead", role="lead"),
    ]
    result = pad_composer_node(state)
    ids = [t.id for t in result["tracks"]]
    assert ids.count("pad") == 1
    assert "melody" in ids
    print("✓ test_pad_composer_merges_tracks OK")


def test_chord_at_bar_cycles():
    plan = build_harmony_plan(
        sections=["verse"],
        key="C",
        mode="minor",
    )
    sh = plan.sections[0]
    c0 = chord_at_bar(sh, 0)
    c4 = chord_at_bar(sh, 4)
    assert c0.root_degree == c4.root_degree or len(sh.progression) > 1
    pitches = chord_pitches("C", "minor", c0)
    assert len(pitches) == 3
    print("✓ test_chord_at_bar_cycles OK")


if __name__ == "__main__":
    test_harmony_planner_node()
    test_bass_follows_chord_roots()
    test_pad_skips_sparse_breakdown()
    test_pad_composer_merges_tracks()
    test_chord_at_bar_cycles()
    print("\n✓ All harmony phase 3 tests passed")
