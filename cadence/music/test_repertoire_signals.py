"""Tests de señales generales de repertorio (sin tags de género)."""

from cadence.music.repertoire_signals import (
    enrich_orchestration_from_strategies,
    instruments_implied_by_strategies,
    percussion_suppressed,
    resolve_harmony_pool_choice,
)
from cadence.music.strategy_pools import select_strategies
from cadence.schemas.song_state import GenerationStrategies, OrchestrationPlan, InstrumentAssignment


def test_high_energy_implies_dense_layers():
    s = select_strategies(42, [], "minor", "game", 5)
    implied = instruments_implied_by_strategies(s, energy_level=5, use_case="game")
    assert "arp_synth" in implied
    assert "echo_synth" in implied


def test_loop_suppresses_percussion():
    assert percussion_suppressed(use_case="loop", energy_level=1) is True
    assert percussion_suppressed(use_case="game", energy_level=5) is False


def test_enrich_adds_missing_arp_and_echo():
    strategies = GenerationStrategies(
        generation_seed=1,
        drum_pattern="techno",
        bass_pattern="pulse",
        harmony_pool="aggressive",
        arp_pattern="sixteenth",
        counter_pattern="offbeat_sync",
        echo_source="melody",
    )
    plan = OrchestrationPlan(
        instruments=[
            InstrumentAssignment(instrument_id="drums", gm_program=0, active=True),
            InstrumentAssignment(instrument_id="bass", gm_program=38, active=True),
            InstrumentAssignment(instrument_id="melody", gm_program=81, active=True),
            InstrumentAssignment(instrument_id="chord_stab", gm_program=62, active=True),
        ],
        drum_pattern="techno",
        bass_pattern="pulse",
    )
    enriched = enrich_orchestration_from_strategies(
        plan, strategies, energy_level=5, use_case="game",
    )
    ids = {a.instrument_id for a in enriched.instruments if a.active}
    assert "arp_synth" in ids
    assert "echo_synth" in ids
    assert enriched.melody_texture == "dense"


def test_harmony_prefers_strategies_at_high_energy():
    pool = resolve_harmony_pool_choice(
        "classic", "aggressive", energy_level=5, use_case="game",
    )
    assert pool == "aggressive"


def test_sparse_loop_enrich_deactivates_drums_with_avoid():
    from cadence.schemas.song_state import MusicalStyleProfile

    plan = OrchestrationPlan(
        instruments=[
            InstrumentAssignment(instrument_id="drums", gm_program=0, active=True),
            InstrumentAssignment(instrument_id="bass", gm_program=38, active=True),
            InstrumentAssignment(instrument_id="melody", gm_program=88, active=True),
        ],
        drum_pattern="default",
        bass_pattern="pulse",
        melody_texture="sparse",
    )
    profile = MusicalStyleProfile(
        genres=["ambient"],
        references=[],
        instrumentation=[],
        avoid=["percussive drums"],
        drum_character="none",
        reasoning="test",
    )
    enriched = enrich_orchestration_from_strategies(
        plan, None, energy_level=1, use_case="loop", style_profile=profile,
    )
    drums = next(a for a in enriched.instruments if a.instrument_id == "drums")
    assert drums.active is False


if __name__ == "__main__":
    test_high_energy_implies_dense_layers()
    test_loop_suppresses_percussion()
    test_enrich_adds_missing_arp_and_echo()
    test_harmony_prefers_strategies_at_high_energy()
    test_sparse_loop_enrich_deactivates_drums_with_avoid()
    print("All repertoire signals tests passed.")
