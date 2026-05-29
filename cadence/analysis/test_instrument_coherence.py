"""Tests de catálogo de timbres."""

from cadence.music.instrument_catalog import (
    apply_orchestration_gm,
    build_fallback_orchestration,
    select_fallback_lead_layers,
)
from cadence.schemas.song_state import RhythmEvent, Track


def test_timbres_vary_by_seed():
    track = Track(
        id="melody", instrument="Lead", instrument_id="melody",
        role="lead", events=[],
    )
    plan_a = build_fallback_orchestration(
        [track], generation_seed=42, drum_pattern="default", bass_pattern="root_fifth",
    )
    plan_b = build_fallback_orchestration(
        [track], generation_seed=9999, drum_pattern="default", bass_pattern="root_fifth",
    )
    mel_a = next(a for a in plan_a.instruments if a.instrument_id == "melody")
    mel_b = next(a for a in plan_b.instruments if a.instrument_id == "melody")
    assert mel_a.gm_program != mel_b.gm_program
    out_a = apply_orchestration_gm([track], plan_a)[0]
    out_b = apply_orchestration_gm([track], plan_b)[0]
    assert out_a.gm_program != out_b.gm_program
    print("✓ test_timbres_vary_by_seed OK")


def test_lead_budget_game_vs_loop():
    game = select_fallback_lead_layers(
        use_case="game", energy_level=5, genre_tags=["techno"],
        generation_seed=99,
    )
    loop = select_fallback_lead_layers(
        use_case="loop", energy_level=1, genre_tags=["ambient"],
        generation_seed=99,
    )
    assert len(game) <= 2
    assert len(loop) == 0
    print(f"  game leads: {game}, loop leads: {loop}")
    print("✓ test_lead_budget_game_vs_loop OK")


if __name__ == "__main__":
    test_timbres_vary_by_seed()
    test_lead_budget_game_vs_loop()
    print("\n✓ All instrument/coherence tests passed")
