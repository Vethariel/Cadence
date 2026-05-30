"""Selección ponderada de patrones y anti-repetición intra-batch."""

from cadence.music.pattern_batch_context import PatternBatchContext
from cadence.music.strategy_pools import _weighted_pick, select_strategies


def test_weighted_pick_deterministic():
    a = _weighted_pick(["techno", "house"], ("techno", "house", "dnb"), 42, 3, field="drum")
    b = _weighted_pick(["techno", "house"], ("techno", "house", "dnb"), 42, 3, field="drum")
    assert a == b
    assert a in ("techno", "house", "dnb")


def test_batch_avoids_repeated_bass():
    with PatternBatchContext() as batch:
        picks = []
        for seed in range(20, 40):
            s = select_strategies(
                seed, ["techno"], "minor", "game", 5,
                composition_archetype="chiptune_dance",
            )
            batch.record(drum=s.drum_pattern, bass=s.bass_pattern, harmony=s.harmony_pool)
            picks.append(s.bass_pattern)
        assert len(set(picks)) >= 3
        assert "root_fifth" not in picks[:3]


def test_medium_energy_bass_not_only_root_fifth():
    from cadence.music.pattern_registry import pattern_family

    s = select_strategies(
        77, ["game"], "minor", "game", 3, composition_archetype="default_game",
    )
    assert pattern_family(s.bass_pattern) in (
        "driving", "syncopated", "walk", "half_time", "octave_pulse", "pulse",
        "root_fifth", "staccato",
    )
    assert pattern_family(s.bass_pattern) != "root_fifth" or s.generation_seed == 77


if __name__ == "__main__":
    test_weighted_pick_deterministic()
    test_batch_avoids_repeated_bass()
    test_medium_energy_bass_not_only_root_fifth()
    print("All pattern_selection tests passed.")
