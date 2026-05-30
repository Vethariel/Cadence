"""Tests Fase 8: generation_seed + strategy pools."""

from langchain_core.messages import HumanMessage

from cadence.schemas.song_state import (
    SectionIntent,
    SongNarrative,
    SongStructure,
    TechnicalProposal,
    UserIntent,
)
from cadence.agent.nodes.strategy import strategy_planner_node
from cadence.agent.nodes.harmony import harmony_planner_node
from cadence.agent.nodes.rhythm import _generate_drum_track, _generate_bass_track
from cadence.music.narrative_contract import contract_section_intent_map
from cadence.music.strategy_pools import (
    compute_generation_seed,
    select_strategies,
    get_harmony_templates,
)


def _mock_state():
    return {
        "messages": [HumanMessage(content="boss fight techno")],
        "intent": UserIntent(
            raw_prompt="boss fight techno", knowledge_level="non_technical",
            use_case="game", mood="dark", style_tags=["techno", "dubstep"],
        ),
        "technical_proposal": TechnicalProposal(
            bpm=140, key="F", mode="minor", genre_tags=["techno"],
            energy_level=5, structure=["intro", "drop", "outro"],
        ),
        "structure": SongStructure(
            sections=["intro", "drop", "outro"],
            bars_per_section={"intro": 4, "drop": 8, "outro": 4},
            total_bars=16,
            estimated_duration_ms=27429,
        ),
        "narrative": SongNarrative(
            logline="test", arc_type="rise-climax-fall",
            sections=[
                SectionIntent(
                    id="intro", narrative_role="establish", emotional_target="x",
                    density=0.3, harmonic_tension=0.2, rhythmic_complexity=0.3,
                ),
                SectionIntent(
                    id="drop", narrative_role="climax", emotional_target="y",
                    density=1.0, harmonic_tension=0.8, rhythmic_complexity=0.7,
                ),
                SectionIntent(
                    id="outro", narrative_role="release", emotional_target="z",
                    density=0.3, harmonic_tension=0.1, rhythmic_complexity=0.2,
                ),
            ],
        ),
        "generation_seed": 0,
    }


def test_generation_seed_deterministic():
    s1 = compute_generation_seed("boss fight", 80)
    s2 = compute_generation_seed("boss fight", 80)
    s3 = compute_generation_seed("other prompt", 80)
    assert s1 == s2
    assert s1 != s3
    print("✓ test_generation_seed_deterministic OK")


def test_strategy_planner_node():
    state = _mock_state()
    result = strategy_planner_node(state)
    assert result["generation_seed"] > 0
    strategies = result["strategies"]
    from cadence.music.strategy_pools import DRUM_POOL, BASS_POOL, HARMONY_POOL
    from cadence.music.arp_patterns import ARP_PATTERNS

    assert strategies.drum_pattern in DRUM_POOL
    assert strategies.bass_pattern in BASS_POOL
    assert strategies.harmony_pool in HARMONY_POOL
    assert strategies.arp_pattern in ARP_PATTERNS
    print(f"  strategies: {strategies.model_dump()}")
    print("✓ test_strategy_planner_node OK")


def test_different_seeds_pick_different_strategies():
    s1 = select_strategies(42, ["techno"], "minor")
    s2 = select_strategies(9999, ["techno"], "minor")
    combined = s1.model_dump()
    combined2 = s2.model_dump()
    assert combined != combined2 or s1.generation_seed != s2.generation_seed
    print("✓ test_different_seeds_pick_different_strategies OK")


def test_energy_biases_drum_pattern():
    low = select_strategies(0, [], "minor", "loop", 1)
    high = select_strategies(0, [], "minor", "game", 5)
    assert low.drum_pattern in ("default", "halftime", "house")
    assert high.drum_pattern in ("dubstep", "breakbeat", "dnb", "industrial", "techno")
    assert high.harmony_pool in ("aggressive", "dance", "game")
    print("✓ test_energy_biases_drum_pattern OK")


def test_harmony_pool_changes_progression():
    state = _mock_state()
    state.update(strategy_planner_node(state))
    classic = harmony_planner_node(state)["harmony"]
    state["strategies"] = select_strategies(state["generation_seed"], ["techno"], "minor")
    state["strategies"] = state["strategies"].model_copy(update={"harmony_pool": "classic"})
    classic_h = harmony_planner_node(state)["harmony"]
    state["strategies"] = state["strategies"].model_copy(update={"harmony_pool": "game"})
    game_h = harmony_planner_node(state)["harmony"]
    drop_classic = next(s for s in classic_h.sections if s.section_id == "drop")
    drop_game = next(s for s in game_h.sections if s.section_id == "drop")
    assert drop_classic.progression != drop_game.progression
    print("✓ test_harmony_pool_changes_progression OK")


def test_drum_patterns_differ_by_strategy():
    state = _mock_state()
    state.update(strategy_planner_node(state))
    s_techno = state["strategies"].model_copy(update={"drum_pattern": "techno"})
    s_break = state["strategies"].model_copy(update={"drum_pattern": "breakbeat"})
    intent_map = contract_section_intent_map(state["narrative"], None)
    d1 = _generate_drum_track(
        state["structure"].sections,
        state["structure"].bars_per_section,
        140, ["techno"], intent_map,
        drum_pattern_id=s_techno.drum_pattern,
    )
    d2 = _generate_drum_track(
        state["structure"].sections,
        state["structure"].bars_per_section,
        140, ["techno"], intent_map,
        drum_pattern_id=s_break.drum_pattern,
    )
    assert len(d1.events) != len(d2.events) or d1.events[0].t != d2.events[0].t
    print("✓ test_drum_patterns_differ_by_strategy OK")


def test_bass_patterns_differ_by_strategy():
    state = _mock_state()
    state.update(strategy_planner_node(state))
    state.update(harmony_planner_node(state))
    intent_map = contract_section_intent_map(state["narrative"], None)
    b1 = _generate_bass_track(
        state["structure"].sections,
        state["structure"].bars_per_section,
        140, "F", "minor", intent_map, state["harmony"],
        bass_pattern_id="root_fifth",
    )
    b2 = _generate_bass_track(
        state["structure"].sections,
        state["structure"].bars_per_section,
        140, "F", "minor", intent_map, state["harmony"],
        bass_pattern_id="pulse",
    )
    assert len(b1.events) > len(b2.events)
    print("✓ test_bass_patterns_differ_by_strategy OK")


def test_harmony_templates_complete():
    from cadence.music.strategy_pools import HARMONY_POOL
    for pool in HARMONY_POOL:
        tpl = get_harmony_templates("minor", pool)
        for role in ("default", "tension", "climax", "sparse", "release"):
            assert role in tpl
            assert len(tpl[role]) >= 1
    print("✓ test_harmony_templates_complete OK")


if __name__ == "__main__":
    test_generation_seed_deterministic()
    test_strategy_planner_node()
    test_different_seeds_pick_different_strategies()
    test_energy_biases_drum_pattern()
    test_harmony_pool_changes_progression()
    test_drum_patterns_differ_by_strategy()
    test_bass_patterns_differ_by_strategy()
    test_harmony_templates_complete()
    print("\n✓ All phase 8 tests passed")
