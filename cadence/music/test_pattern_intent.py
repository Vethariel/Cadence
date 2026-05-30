"""pattern_intent — separación detección de género vs selección por seed."""

from cadence.music.pattern_intent import derive_pattern_intent
from cadence.music.strategy_pools import select_strategies
from cadence.music.style_profile import build_genre_mix


def test_composite_mix_blends_drum_and_harmony_priorities():
    mix = build_genre_mix(
        proposal_tags=["techno", "orchestral", "boss fight"],
        raw_prompt="boss fight techno orchestral",
    )
    intent = derive_pattern_intent(
        genre_mix=mix,
        use_case="game",
        mood="epic",
        energy_level=5,
        composition_archetype="orchestral_boss",
        generation_seed=42,
    )
    from cadence.music.pattern_registry import pattern_family

    assert intent.drum_candidates
    assert intent.harmony_candidates
    top_drums = {pattern_family(p) for p in intent.drum_candidates[:4]}
    top_harm = set(intent.harmony_candidates[:4])
    assert top_drums & {"breakbeat", "industrial", "dubstep"}
    assert top_harm & {"cinematic", "aggressive", "dark"}


def test_select_strategies_uses_pattern_intent_not_flat_tags():
    mix = build_genre_mix(proposal_tags=["techno", "orchestral", "boss fight"])
    intent = derive_pattern_intent(
        genre_mix=mix,
        use_case="game",
        energy_level=5,
        composition_archetype="orchestral_boss",
        generation_seed=99,
    )
    s_a = select_strategies(
        99, [], "minor", "game", 5,
        composition_archetype="orchestral_boss",
        pattern_intent=intent,
    )
    s_b = select_strategies(
        99, ["techno"], "minor", "game", 5,
        composition_archetype="default_game",
    )
    assert s_a.drum_pattern in intent.drum_candidates
    assert s_a.harmony_pool in intent.harmony_candidates
    assert (s_a.drum_pattern, s_a.harmony_pool) != (s_b.drum_pattern, s_b.harmony_pool) or (
        s_a.bass_pattern != s_b.bass_pattern
    )


def test_different_seeds_same_intent_differ():
    mix = build_genre_mix(proposal_tags=["techno", "dubstep"])
    intent = derive_pattern_intent(
        genre_mix=mix, use_case="game", energy_level=5, generation_seed=1,
    )
    a = select_strategies(1, pattern_intent=intent)
    b = select_strategies(999, pattern_intent=intent)
    combined_a = (a.drum_pattern, a.bass_pattern, a.harmony_pool)
    combined_b = (b.drum_pattern, b.bass_pattern, b.harmony_pool)
    assert combined_a != combined_b


if __name__ == "__main__":
    test_composite_mix_blends_drum_and_harmony_priorities()
    test_select_strategies_uses_pattern_intent_not_flat_tags()
    test_different_seeds_same_intent_differ()
    print("All pattern_intent tests passed.")
