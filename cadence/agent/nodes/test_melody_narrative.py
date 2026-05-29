"""Tests unitarios de variación melódica narrativa (sin LLM)."""

from cadence.agent.nodes.melody import MelodyNote, _vary_pattern_for_bar
from cadence.agent.nodes.narrative_apply import melody_should_play
from cadence.schemas.song_state import SectionIntent


def _sample_pattern() -> list[MelodyNote]:
    return [
        MelodyNote(scale_degree=0, duration_steps=4, velocity=80),
        MelodyNote(scale_degree=2, duration_steps=4, velocity=90),
        MelodyNote(scale_degree=4, duration_steps=4, velocity=85),
        MelodyNote(scale_degree=0, duration_steps=4, velocity=75, is_rest=True),
    ]


def test_vary_pattern_a_prime():
    pattern = _sample_pattern()
    varied = _vary_pattern_for_bar(pattern, bar_idx=1, global_motif=[0, 2, 4])
    assert varied[0].scale_degree == 1
    assert varied[1].scale_degree == 3
    assert varied[3].is_rest
    print("✓ test_vary_pattern_a_prime OK")


def test_vary_pattern_motif_bar():
    pattern = _sample_pattern()
    varied = _vary_pattern_for_bar(pattern, bar_idx=2, global_motif=[5, 3, 1])
    assert varied[0].scale_degree == 5
    assert varied[1].scale_degree == 3
    assert varied[2].scale_degree == 1
    print("✓ test_vary_pattern_motif_bar OK")


def test_melody_should_play_silence():
    silent = SectionIntent(
        id="breakdown", narrative_role="silence", emotional_target="void",
        density=0.0, harmonic_tension=0.0, rhythmic_complexity=0.0,
    )
    assert melody_should_play(silent) is False
    sparse = SectionIntent(
        id="intro", narrative_role="establish", emotional_target="calm",
        density=0.15, harmonic_tension=0.1, rhythmic_complexity=0.2,
    )
    assert melody_should_play(sparse) is False
    dense = SectionIntent(
        id="drop", narrative_role="climax", emotional_target="power",
        density=0.8, harmonic_tension=0.7, rhythmic_complexity=0.6,
    )
    assert melody_should_play(dense) is True
    print("✓ test_melody_should_play_silence OK")


if __name__ == "__main__":
    test_vary_pattern_a_prime()
    test_vary_pattern_motif_bar()
    test_melody_should_play_silence()
    print("\n✓ All melody narrative tests passed")
