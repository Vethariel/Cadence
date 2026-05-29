"""Tests Fase 6b: arp_synth + echo_synth."""

from langchain_core.messages import HumanMessage

import cadence.instruments  # noqa: F401
from cadence.schemas.song_state import (
    DevelopmentPlan,
    SectionDevelopment,
    SectionIntent,
    SongNarrative,
    SongStructure,
    TechnicalProposal,
    UserIntent,
)
from cadence.agent.nodes.arrangement import arrangement_planner_node
from cadence.agent.nodes.harmony import harmony_planner_node
from cadence.instruments.context import build_compose_context
from cadence.instruments.registry import compose_layer, list_instruments
from cadence.music.arp_patterns import (
    build_arp_pitch_sequence,
    generate_bar_arp,
    pattern_for_seed,
)
from cadence.music.harmony_theory import chord_pitches
from cadence.schemas.song_state import ChordSpec


def _boss_fight_state():
    narrative = SongNarrative(
        logline="Boss awakens and escalates to collapse",
        arc_type="rise-climax-fall",
        global_motif=[0, 2, 4],
        sections=[
            SectionIntent(
                id="intro", narrative_role="establish", emotional_target="mystery",
                density=0.3, harmonic_tension=0.2, rhythmic_complexity=0.3,
            ),
            SectionIntent(
                id="build-up", narrative_role="tension", emotional_target="urgency",
                density=0.7, harmonic_tension=0.6, rhythmic_complexity=0.6,
            ),
            SectionIntent(
                id="drop", narrative_role="climax", emotional_target="triumph",
                density=1.0, harmonic_tension=0.8, rhythmic_complexity=0.7,
            ),
            SectionIntent(
                id="outro", narrative_role="release", emotional_target="calm",
                density=0.3, harmonic_tension=0.1, rhythmic_complexity=0.2,
            ),
        ],
    )
    return {
        "messages": [HumanMessage(content="boss fight techno")],
        "intent": UserIntent(
            raw_prompt="boss fight", knowledge_level="non_technical",
            use_case="game", mood="dark", style_tags=["techno"],
        ),
        "technical_proposal": TechnicalProposal(
            bpm=140, key="F", mode="minor", genre_tags=["techno"],
            energy_level=5, structure=["intro", "build-up", "drop", "outro"],
        ),
        "structure": SongStructure(
            sections=["intro", "build-up", "drop", "outro"],
            bars_per_section={"intro": 4, "build-up": 8, "drop": 8, "outro": 4},
            total_bars=24,
            estimated_duration_ms=41143,
        ),
        "narrative": narrative,
        "development": DevelopmentPlan(
            global_motif=[0, 2, 4],
            generation_seed=42,
            sections=[
                SectionDevelopment(section_id=s, transform="introduce")
                for s in ["intro", "build-up", "drop", "outro"]
            ],
        ),
        "generation_seed": 42,
        "tracks": [],
    }


def test_registry_has_arp_synth():
    assert "arp_synth" in list_instruments()
    assert "echo_synth" in list_instruments()
    print("✓ test_registry_has_arp_synth OK")


def test_arp_pattern_from_seed():
    assert pattern_for_seed(0) == "up"
    assert pattern_for_seed(1) == "down"
    assert pattern_for_seed(2) == "pingpong"
    assert pattern_for_seed(3) == "up"
    print("✓ test_arp_pattern_from_seed OK")


def test_arp_pitch_sequence_direction():
    pitches = [60, 63, 67]
    up = build_arp_pitch_sequence(pitches, "up")
    down = build_arp_pitch_sequence(pitches, "down")
    assert up[0] < up[-1]
    assert down[0] > down[-1]
    print("✓ test_arp_pitch_sequence_direction OK")


def test_generate_bar_arp_produces_sixteenth_density():
    chord = ChordSpec(root_degree=0, quality="minor", bars=1)
    pitches = chord_pitches("F", "minor", chord, octave=4)
    events = generate_bar_arp(
        pitches=pitches,
        pattern="up",
        step_ms=107.14,
        bar_start_t=0,
        beat_index=0,
        section="drop",
        base_velocity=50,
        note_stride=1,
    )
    assert len(events) == 16
    assert all(e.type == "note" for e in events)
    assert len({e.pitch for e in events}) >= 3
    print("✓ test_generate_bar_arp_produces_sixteenth_density OK")


def test_arrangement_includes_arp_on_high_density():
    state = _boss_fight_state()
    arrangement = arrangement_planner_node(state)["arrangement"]
    layer_ids = [l.instrument_id for l in arrangement.layers]
    assert "arp_synth" in layer_ids
    assert "echo_synth" in layer_ids
    print(f"  layers: {layer_ids}")
    print("✓ test_arrangement_includes_arp_on_high_density OK")


def test_compose_arp_synth_follows_harmony():
    state = _boss_fight_state()
    state["harmony"] = harmony_planner_node(state)["harmony"]
    state["arrangement"] = arrangement_planner_node(state)["arrangement"]
    arp_layer = next(l for l in state["arrangement"].layers if l.instrument_id == "arp_synth")
    ctx = build_compose_context(state, arp_layer)
    track = compose_layer(ctx)
    assert track is not None
    assert track.id == "arp_synth"
    drop_notes = [e for e in track.events if e.section == "drop"]
    intro_notes = [e for e in track.events if e.section == "intro"]
    assert len(drop_notes) > len(intro_notes)
    assert len(drop_notes) >= 64
    print("✓ test_compose_arp_synth_follows_harmony OK")


def test_arp_respects_layer_schedule():
    state = _boss_fight_state()
    state["harmony"] = harmony_planner_node(state)["harmony"]
    state["arrangement"] = arrangement_planner_node(state)["arrangement"]
    arp_layer = next(l for l in state["arrangement"].layers if l.instrument_id == "arp_synth")
    ctx = build_compose_context(state, arp_layer)
    track = compose_layer(ctx)
    assert track is not None
    sections = {e.section for e in track.events}
    assert "outro" not in sections
    print("✓ test_arp_respects_layer_schedule OK")


if __name__ == "__main__":
    test_registry_has_arp_synth()
    test_arp_pattern_from_seed()
    test_arp_pitch_sequence_direction()
    test_generate_bar_arp_produces_sixteenth_density()
    test_arrangement_includes_arp_on_high_density()
    test_compose_arp_synth_follows_harmony()
    test_arp_respects_layer_schedule()
    print("\n✓ All phase 6b tests passed")
