"""Tests de afinidad por categoría del catálogo y diversidad de combos."""

from cadence.music.genre_catalog import (
    category_for_genre,
    category_mix_from_genres,
    category_mix_from_genre_mix,
    dominant_category,
)
from cadence.music.genre_category_patterns import (
    rhythm_ladder_bias_from_categories,
    apply_category_boosts,
)
from cadence.music.pattern_batch_context import (
    PatternBatchContext,
    clear_service_combo_memory,
    combo_in_recent_window,
    pattern_signature,
    service_combo_diversity_window,
)
from cadence.music.pattern_selection import compute_candidate_weights
from cadence.music.strategy_pools import select_strategies


def test_category_for_dnb_and_boss_alias():
    assert category_for_genre("dnb") == "electronic_dance"
    assert category_for_genre("boss") == "game_context"
    assert category_for_genre("8bit") == "synth_retro_game"
    print("✓ test_category_for_dnb_and_boss_alias OK")


def test_category_mix_from_tags():
    mix = category_mix_from_genres(["dubstep", "brostep", "dark"])
    assert "bass_and_beats" in mix or "industrial_dark" in mix
    dom = dominant_category(mix)
    assert dom is not None
    print(f"  mix={mix} dominant={dom}")
    print("✓ test_category_mix_from_tags OK")


def test_category_boost_changes_drum_weights():
    candidates = ["techno_a", "dnb_a", "breakbeat_a", "halftime_a"]
    w_neutral = compute_candidate_weights(
        candidates,
        genre_mix={},
        genre_boost_table={},
        field="drum",
        energy_level=5,
    )
    w_categorized = compute_candidate_weights(
        candidates,
        genre_mix={"drum and bass": 1.0},
        genre_boost_table={},
        field="drum",
        energy_level=5,
    )
    assert w_categorized.get("dnb_a", 0) > w_neutral.get("dnb_a", 0)
    assert w_categorized.get("dnb_a", 0) > w_categorized.get("halftime_a", 0)
    print("✓ test_category_boost_changes_drum_weights OK")


def test_ladder_bias_from_category_not_literal_tag():
    bias = rhythm_ladder_bias_from_categories(
        category_mix_from_genres(["chiptune", "arcade"]),
        energy_level=5,
    )
    assert bias == "dance"
    print("✓ test_ladder_bias_from_category_not_literal_tag OK")


def test_combo_diversity_in_batch_context():
    clear_service_combo_memory()
    with PatternBatchContext(combo_window=3) as batch:
        seen: list[str] = []
        for seed in range(50, 80):
            s = select_strategies(seed, ["techno"], "minor", "game", 4)
            batch.record(
                drum=s.drum_pattern, bass=s.bass_pattern, harmony=s.harmony_pool,
            )
            seen.append(
                pattern_signature(
                    drum=s.drum_pattern, bass=s.bass_pattern, harmony=s.harmony_pool,
                ),
            )
        assert len(set(seen)) >= 4
    print("✓ test_combo_diversity_in_batch_context OK")


def test_combo_in_recent_window():
    sig = pattern_signature(drum="techno_a", bass="driving_a", harmony="dark")
    with PatternBatchContext(combo_window=2) as batch:
        batch._signatures.append(sig)
        assert combo_in_recent_window(
            drum="techno_a", bass="driving_a", harmony="dark",
        )
        assert not combo_in_recent_window(
            drum="house_a", bass="pulse_a", harmony="game",
        )
    print("✓ test_combo_in_recent_window OK")


if __name__ == "__main__":
    test_category_for_dnb_and_boss_alias()
    test_category_mix_from_tags()
    test_category_boost_changes_drum_weights()
    test_ladder_bias_from_category_not_literal_tag()
    test_combo_diversity_in_batch_context()
    test_combo_in_recent_window()
    print("\n✓ All genre_category tests passed")
