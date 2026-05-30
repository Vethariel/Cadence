"""Tests de subdivisión de desarrollo motivico (general, por use_case y longitud)."""

from cadence.schemas.song_state import SectionIntent
from cadence.music.development_theory import (
    build_section_development,
    build_section_segments,
    development_for_bar,
    segment_count_for_section,
    variation_need,
)


def test_loop_low_variation_long_section():
    n = segment_count_for_section(
        32, use_case="loop", narrative_role="climax", density=1.0,
    )
    game_n = segment_count_for_section(
        32, use_case="game", narrative_role="climax", density=1.0,
    )
    assert n < game_n
    assert n <= 3
    print(f"  loop segments={n}  game segments={game_n}")
    print("✓ test_loop_low_variation_long_section OK")


def test_game_long_drop_splits():
    n = segment_count_for_section(
        56, use_case="game", narrative_role="climax", density=1.0,
    )
    assert n >= 4
    segs = build_section_segments(
        "drop",
        56,
        SectionIntent(
            id="drop", narrative_role="climax", emotional_target="triumph",
            density=1.0, harmonic_tension=0.9, rhythmic_complexity=0.8,
        ),
        [0, 2, 4, 2],
        seed=42,
        use_case="game",
        energy_level=5,
    )
    assert len(segs) == n
    transforms = {s.transform for s in segs}
    contours = {s.contour for s in segs}
    assert len(transforms) >= 2 or len(contours) >= 2
    covered = sum(s.end_bar - s.start_bar for s in segs)
    assert covered == 56
    print(f"  56-bar drop → {len(segs)} segments")
    print("✓ test_game_long_drop_splits OK")


def test_short_section_single_block():
    dev = build_section_development(
        "intro", None, [0, 2, 4], 1,
        section_bars=4, use_case="game",
    )
    assert dev.segments == []
    assert segment_count_for_section(4, use_case="game", narrative_role="establish", density=0.3) == 1
    print("✓ test_short_section_single_block OK")


def test_development_for_bar_switches_mid_section():
    dev = build_section_development(
        "drop",
        SectionIntent(
            id="drop", narrative_role="climax", emotional_target="x",
            density=1.0, harmonic_tension=0.8, rhythmic_complexity=0.7,
        ),
        [0, 2, 4],
        99,
        section_bars=16,
        use_case="game",
        energy_level=5,
    )
    assert len(dev.segments) >= 2
    per_bar = [development_for_bar(dev, s.start_bar) for s in dev.segments]
    assert any(
        per_bar[i].transform != per_bar[j].transform or per_bar[i].motif_variant != per_bar[j].motif_variant
        for i in range(len(per_bar))
        for j in range(i + 1, len(per_bar))
    )
    print("✓ test_development_for_bar_switches_mid_section OK")


def test_variation_need_game_above_loop():
    assert variation_need(use_case="game", narrative_role="climax", density=1.0) > variation_need(
        use_case="loop", narrative_role="climax", density=1.0,
    )
    print("✓ test_variation_need_game_above_loop OK")


if __name__ == "__main__":
    test_loop_low_variation_long_section()
    test_game_long_drop_splits()
    test_short_section_single_block()
    test_development_for_bar_switches_mid_section()
    test_variation_need_game_above_loop()
    print("\n✓ All development_theory tests passed")
