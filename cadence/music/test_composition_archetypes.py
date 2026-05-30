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


def test_suppresses_ensemble():
    from cadence.music.composition_archetypes import suppresses_ensemble

    assert suppresses_ensemble("energetic_game")
    assert suppresses_ensemble("compact_action")
    assert suppresses_ensemble("chiptune_dance")  # alias → dense_dance
    assert not suppresses_ensemble("orchestral_boss")
    assert not suppresses_ensemble("hybrid_epic")


def test_archetype_optional_budget():
    from cadence.music.composition_archetypes import archetype_optional_budget

    assert archetype_optional_budget("energetic_game", 4, "game") == (3, 2)
    assert archetype_optional_budget("orchestral_boss", 5, "game") == (5, 3)


if __name__ == "__main__":
    test_twelve_canonical_archetypes()
    test_legacy_aliases_normalize()
    test_unknown_defaults()
    test_all_accepted_includes_legacy()
    test_policy_families()
    test_suppresses_ensemble()
    test_archetype_optional_budget()
    print("All composition_archetypes tests passed.")
