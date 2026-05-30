"""Umbrales de densidad melódica por arquetipo."""

from cadence.music.melody_density_policy import (
    is_dense_melody_target,
    melody_max_long_gap_ratio,
    melody_min_notes_per_bar_validator,
    melody_notes_per_bar_target,
    melody_rest_ratio_for_intent,
)
from cadence.schemas.song_state import SectionIntent


def test_chiptune_dense_targets():
    assert is_dense_melody_target("chiptune_dance", energy_level=5)
    assert melody_notes_per_bar_target("chiptune_dance", 5) >= 8
    assert melody_min_notes_per_bar_validator("chiptune_dance", 5) == 5.5
    assert melody_max_long_gap_ratio("chiptune_dance", 5) == 0.18


def test_default_game_dense_texture():
    assert is_dense_melody_target(
        "default_game", energy_level=4, melody_texture="dense",
    )
    assert melody_notes_per_bar_target(
        "default_game", 5, melody_texture="dense", narrative_role="climax",
    ) >= 7


def test_sparse_archetype_no_validator_threshold():
    assert melody_min_notes_per_bar_validator("ambient_loop", 2) is None
    assert melody_max_long_gap_ratio("ambient_loop", 2) is None


def test_chiptune_low_rest_ratio():
    intent = SectionIntent(
        id="drop", narrative_role="climax", emotional_target="x",
        density=1.0, harmonic_tension=0.8, rhythmic_complexity=0.7,
    )
    assert melody_rest_ratio_for_intent(
        intent, composition_archetype="chiptune_dance", energy_level=5,
    ) <= 0.05


if __name__ == "__main__":
    test_chiptune_dense_targets()
    test_default_game_dense_texture()
    test_sparse_archetype_no_validator_threshold()
    test_chiptune_low_rest_ratio()
    print("All melody_density_policy tests passed.")
