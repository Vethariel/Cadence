"""Tests unitarios de fraseo melódico (sin LLM)."""

from cadence.agent.nodes.melody import MelodyNote, MelodyPhrase
from cadence.music.melody_phrases import fix_phrase_steps, apply_development_to_notes
from cadence.music.development_theory import build_development_plan
from cadence.schemas.song_state import SectionIntent


def test_fix_phrase_steps_pads():
    notes = [
        MelodyNote(scale_degree=0, duration_steps=4, velocity=80),
        MelodyNote(scale_degree=2, duration_steps=4, velocity=80),
    ]
    fixed = fix_phrase_steps(notes, 32)
    assert sum(n.duration_steps for n in fixed) == 32
    print("✓ test_fix_phrase_steps_pads OK")


def test_invert_transform():
    notes = [MelodyNote(scale_degree=0, duration_steps=4, velocity=80)]
    dev = build_development_plan(
        sections=["s"],
        global_motif=[0, 2, 4],
        narrative_sections={
            "s": SectionIntent(
                id="s", narrative_role="reflection", emotional_target="dread",
                density=0.3, harmonic_tension=0.3, rhythmic_complexity=0.2,
            ),
        },
        generation_seed=7,
    ).sections[0]
    assert dev.transform == "fragment"
    inverted = build_development_plan(
        sections=["s"],
        global_motif=[0, 2, 4],
        narrative_sections={
            "s": SectionIntent(
                id="s", narrative_role="tension", emotional_target="urgency",
                density=0.7, harmonic_tension=0.6, rhythmic_complexity=0.5,
            ),
        },
        generation_seed=7,
    ).sections[0]
    assert inverted.transform == "sequence_up"
    print("✓ test_invert_transform OK")


if __name__ == "__main__":
    test_fix_phrase_steps_pads()
    test_invert_transform()
    print("\n✓ melody phrase tests OK")
