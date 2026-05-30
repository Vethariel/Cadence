"""Tests del registro central de arquetipos compositivos."""

from cadence.music.composition_archetypes import (
    COMPOSITION_ARCHETYPES,
    ALL_ACCEPTED_ARCHETYPES,
    normalize_archetype,
    policy_family,
)


def test_twelve_canonical_archetypes():
    assert len(COMPOSITION_ARCHETYPES) == 12


def test_legacy_aliases_normalize():
    assert normalize_archetype("ambient_loop") == "sparse_loop"
    assert normalize_archetype("chiptune_dance") == "dense_dance"
    assert normalize_archetype("boss_orchestral") == "orchestral_boss"


def test_unknown_defaults():
    assert normalize_archetype("") == "default_game"
    assert normalize_archetype("not_an_archetype") == "default_game"


def test_all_accepted_includes_legacy():
    assert "ambient_loop" in ALL_ACCEPTED_ARCHETYPES
    assert "sparse_loop" in ALL_ACCEPTED_ARCHETYPES


def test_policy_families():
    assert policy_family("lofi_downtempo") == "sparse"
    assert policy_family("energetic_game") == "energetic"
    assert policy_family("industrial_combat") == "dense"
    assert policy_family("hybrid_epic") == "orchestral"


if __name__ == "__main__":
    test_twelve_canonical_archetypes()
    test_legacy_aliases_normalize()
    test_unknown_defaults()
    test_all_accepted_includes_legacy()
    test_policy_families()
    print("All composition_archetypes tests passed.")
