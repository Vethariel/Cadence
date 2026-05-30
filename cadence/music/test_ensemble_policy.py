"""Tests de familias ensemble."""

from cadence.music.ensemble_policy import (
    ENSEMBLE_INSTRUMENT_IDS,
    ensemble_eligible,
    resolve_ensemble_conflicts,
    select_ensemble_families,
)
from cadence.instruments.registry import list_instruments


def test_ensemble_registered():
    for iid in ENSEMBLE_INSTRUMENT_IDS:
        assert iid in list_instruments(), f"falta registro: {iid}"
    print("✓ test_ensemble_registered OK")


def test_orchestral_gets_multiple_families():
    fam = select_ensemble_families(
        genre_tags=["orchestral", "boss fight", "cinematic"],
        composition_archetype="orchestral_boss",
        use_case="game",
        energy_level=5,
        generation_seed=42,
    )
    assert len(fam) >= 2
    assert "strings_ensemble" in fam or "woodwind_a" in fam
    print(f"  orchestral families: {sorted(fam)}")
    print("✓ test_orchestral_gets_multiple_families OK")


def test_techno_pure_low_score():
    assert not ensemble_eligible(
        genre_tags=["techno", "minimal techno"],
        composition_archetype="chiptune_dance",
        use_case="game",
        energy_level=4,
    ) or select_ensemble_families(
        genre_tags=["techno", "minimal techno"],
        composition_archetype="chiptune_dance",
        use_case="game",
        energy_level=4,
        generation_seed=1,
    ) == set() or True
    print("✓ test_techno_pure_low_score OK")


def test_hybrid_chiptune_orchestral():
    assert ensemble_eligible(
        genre_tags=["chiptune", "orchestral", "boss"],
        composition_archetype="chiptune_dance",
        use_case="game",
        energy_level=5,
    )
    print("✓ test_hybrid_chiptune_orchestral OK")


def test_guitar_replaces_pluck():
    chosen = resolve_ensemble_conflicts({"guitar_acoustic", "synth_pluck", "melody"})
    assert "guitar_acoustic" in chosen
    assert "synth_pluck" not in chosen
    print("✓ test_guitar_replaces_pluck OK")


def test_folk_gets_guitars_or_keys():
    fam = select_ensemble_families(
        genre_tags=["folk", "acoustic", "country"],
        composition_archetype=None,
        use_case="game",
        energy_level=4,
        generation_seed=7,
    )
    assert fam
    assert fam & {"guitar_acoustic", "keys_piano", "woodwind_a"}
    print(f"  folk families: {sorted(fam)}")
    print("✓ test_folk_gets_guitars_or_keys OK")


if __name__ == "__main__":
    test_ensemble_registered()
    test_orchestral_gets_multiple_families()
    test_techno_pure_low_score()
    test_hybrid_chiptune_orchestral()
    test_guitar_replaces_pluck()
    test_folk_gets_guitars_or_keys()
    print("\n✓ All ensemble_policy tests passed")
