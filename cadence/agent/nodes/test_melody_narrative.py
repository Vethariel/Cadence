"""Tests unitarios de variación melódica narrativa (sin LLM)."""

from cadence.agent.nodes.melody import MelodyNote
from cadence.music.melody_phrases import apply_development_to_notes
from cadence.music.development_theory import build_development_plan
from cadence.agent.nodes.narrative_apply import melody_should_play
from cadence.schemas.song_state import SectionIntent


def test_development_varies_phrase():
    notes = [
        MelodyNote(scale_degree=0, duration_steps=4, velocity=80),
        MelodyNote(scale_degree=2, duration_steps=4, velocity=90),
        MelodyNote(scale_degree=4, duration_steps=4, velocity=85),
        MelodyNote(scale_degree=0, duration_steps=4, velocity=75, is_rest=True),
    ]
    dev = build_development_plan(["drop"], [0, 2, 4], generation_seed=3).sections[0]
    a = apply_development_to_notes(notes, dev, cycle_idx=0, phrase_idx=0)
    b = apply_development_to_notes(notes, dev, cycle_idx=0, phrase_idx=1)
    assert a[0].scale_degree != b[0].scale_degree or a[1].scale_degree != b[1].scale_degree
    print("✓ test_development_varies_phrase OK")


def test_melody_should_play_silence():
    silent = SectionIntent(
        id="breakdown", narrative_role="silence", emotional_target="void",
        density=0.0, harmonic_tension=0.0, rhythmic_complexity=0.0,
    )
    assert melody_should_play(silent) is False
    dense = SectionIntent(
        id="drop", narrative_role="climax", emotional_target="power",
        density=0.8, harmonic_tension=0.7, rhythmic_complexity=0.6,
    )
    assert melody_should_play(dense) is True
    print("✓ test_melody_should_play_silence OK")


if __name__ == "__main__":
    test_development_varies_phrase()
    test_melody_should_play_silence()
    print("\n✓ All melody narrative tests passed")
