"""Tests de política de textura y schedule por segmentos."""

from cadence.schemas.song_state import (
    DevelopmentPlan,
    DevelopmentSegment,
    SectionDevelopment,
    SectionIntent,
    SongStructure,
)
from cadence.music.texture_policy import (
    build_segment_schedule_pending,
    infer_texture_mode,
    segment_layer_delta,
    schedule_core_layers,
)
from cadence.music.layer_schedule import build_layer_schedule, active_layers_at_bar
from cadence.music.harmony_theory import build_harmony_plan


def test_infer_bedded_for_loop():
    assert infer_texture_mode(use_case="loop", energy_level=1) == "bedded"
    assert infer_texture_mode(use_case="cutscene", energy_level=3) == "bedded"
    print("✓ test_infer_bedded_for_loop OK")


def test_schedule_core_loop_has_pad():
    core = schedule_core_layers(use_case="loop", energy_level=2, percussion_suppressed=True)
    assert "pad" in core and "bass" in core
    print("✓ test_schedule_core_loop_has_pad OK")


def test_segment_climax_adds_arp():
    add, remove = segment_layer_delta(
        "climax",
        texture_mode="simultaneous",
        use_case="game",
        available={"pad", "bass", "melody", "arp_synth", "countermelody"},
    )
    assert "arp_synth" in add
    assert "pad" not in remove
    print("✓ test_segment_climax_adds_arp OK")


def test_segment_schedule_entries_on_long_section():
    structure = SongStructure(
        sections=["drop"],
        bars_per_section={"drop": 16},
        total_bars=16,
        estimated_duration_ms=27000,
    )
    dev = DevelopmentPlan(
        global_motif=[0, 2, 4],
        generation_seed=1,
        texture_mode="simultaneous",
        sections=[
            SectionDevelopment(
                section_id="drop",
                transform="climax",
                phrase_length_bars=2,
                contour="saw",
                motif_variant=[0, 2, 4],
                segments=[
                    DevelopmentSegment(
                        start_bar=0, end_bar=8, transform="introduce",
                        phrase_length_bars=2, contour="arch", motif_variant=[0, 2],
                    ),
                    DevelopmentSegment(
                        start_bar=8, end_bar=16, transform="climax",
                        phrase_length_bars=2, contour="saw", motif_variant=[0, 3, 4],
                    ),
                ],
            ),
        ],
    )
    intent = SectionIntent(
        id="drop", narrative_role="climax", emotional_target="x",
        density=1.0, harmonic_tension=0.8, rhythmic_complexity=0.7,
    )
    pending = build_segment_schedule_pending(
        structure, dev,
        {"pad", "bass", "melody", "arp_synth", "countermelody"},
        {"drop": intent},
        use_case="game",
        texture_mode="simultaneous",
    )
    assert any(p[0] == 8 and p[1] == "add" for p in pending)
    print("✓ test_segment_schedule_entries_on_long_section OK")


def test_loop_harmony_has_chord_changes():
    plan = build_harmony_plan(
        ["main"], "C", "minor",
        {"main": SectionIntent(
            id="main", narrative_role="establish", emotional_target="calm",
            density=0.3, harmonic_tension=0.2, rhythmic_complexity=0.2,
        )},
        use_case="loop",
    )
    prog = plan.sections[0].progression
    assert len(prog) >= 2
    assert sum(c.bars for c in prog) >= 4
    print("✓ test_loop_harmony_has_chord_changes OK")


def test_bedded_schedule_pad_from_bar_zero():
    structure = SongStructure(
        sections=["a"],
        bars_per_section={"a": 8},
        total_bars=8,
        estimated_duration_ms=14000,
    )
    sched = build_layer_schedule(
        structure,
        ["bass", "melody", "pad"],
        {"a": SectionIntent(
            id="a", narrative_role="establish", emotional_target="c",
            density=0.3, harmonic_tension=0.2, rhythmic_complexity=0.2,
        )},
        use_case="loop",
        energy_level=2,
        texture_mode="bedded",
        percussion_suppressed=True,
    )
    active0 = active_layers_at_bar(sched, 0, {"bass", "melody", "pad"})
    assert "pad" in active0
    print("✓ test_bedded_schedule_pad_from_bar_zero OK")


if __name__ == "__main__":
    test_infer_bedded_for_loop()
    test_schedule_core_loop_has_pad()
    test_segment_climax_adds_arp()
    test_segment_schedule_entries_on_long_section()
    test_loop_harmony_has_chord_changes()
    test_bedded_schedule_pad_from_bar_zero()
    print("\n✓ All texture_policy tests passed")
