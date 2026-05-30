"""Tests de variación por micro-arco."""

from cadence.schemas.song_state import (
    ChordSpec,
    DevelopmentPlan,
    DevelopmentSegment,
    HarmonyPlan,
    SectionDevelopment,
    SectionHarmony,
    SectionIntent,
)
from cadence.music.development_theory import build_section_development, build_development_plan
from cadence.music.harmony_theory import build_harmony_plan, chord_at_bar
from cadence.music.segment_variation import (
    enrich_harmony_with_segments,
    pattern_id_for_segment,
    segment_cue_label,
    boost_texture_mode_for_segments,
)
from cadence.music.strategy_pools import DRUM_POOL, BASS_POOL
from cadence.music.pattern_registry import pattern_family


def test_pattern_rotates_within_family():
    base = "techno_a"
    a = pattern_id_for_segment(base, 0, "introduce", 1, DRUM_POOL)
    b = pattern_id_for_segment(base, 1, "climax", 1, DRUM_POOL)
    assert pattern_family(a) == pattern_family(b) == "techno"
    assert a == base or pattern_family(a) == "techno"
    print(f"  drum seg0={a} seg1={b}")
    print("✓ test_pattern_rotates_within_family OK")


def test_enrich_harmony_changes_mid_drop():
    intent = SectionIntent(
        id="drop", narrative_role="climax", emotional_target="x",
        density=1.0, harmonic_tension=0.85, rhythmic_complexity=0.8,
    )
    dev = build_section_development(
        "drop", intent, [0, 2, 4], 42,
        section_bars=16, use_case="game", energy_level=5,
    )
    assert len(dev.segments) >= 2
    harmony = build_harmony_plan(["drop"], "C", "minor", {"drop": intent})
    enriched = enrich_harmony_with_segments(
        harmony,
        DevelopmentPlan(
            global_motif=[0, 2, 4],
            sections=[dev],
            generation_seed=42,
            texture_mode="staggered",
        ),
        {"drop": intent},
        seed=42,
    )
    sh = enriched.sections[0]
    chords = [chord_at_bar(sh, b) for b in range(16)]
    roots = [c.root_degree for c in chords]
    assert len(set(roots)) >= 2, f"armonía plana: {roots}"
    print(f"  roots across drop: {roots[:8]}…")
    print("✓ test_enrich_harmony_changes_mid_drop OK")


def test_boost_texture_for_long_climax():
    intent = SectionIntent(
        id="drop", narrative_role="climax", emotional_target="x",
        density=1.0, harmonic_tension=0.9, rhythmic_complexity=0.8,
    )
    plan = build_development_plan(
        ["drop"],
        [0, 2, 4],
        {"drop": intent},
        generation_seed=1,
        energy_level=5,
        bars_per_section={"drop": 24},
        use_case="game",
    )
    boosted = boost_texture_mode_for_segments(
        plan.texture_mode, plan, use_case="game", energy_level=5,
        narrative_sections={"drop": intent},
    )
    assert boosted == "simultaneous"
    print("✓ test_boost_texture_for_long_climax OK")


def test_segment_cue_label():
    assert segment_cue_label("drop", 0) == "drop_1"
    assert segment_cue_label("main loop", 2) == "main loop_3"
    print("✓ test_segment_cue_label OK")


if __name__ == "__main__":
    test_pattern_rotates_within_family()
    test_enrich_harmony_changes_mid_drop()
    test_boost_texture_for_long_climax()
    test_segment_cue_label()
    print("\n✓ All segment_variation tests passed")
