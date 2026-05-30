"""Tests de variación contramelodía / pad / eco."""

from cadence.schemas.song_state import SectionDevelopment, DevelopmentSegment
from cadence.music.layer_voice_variation import (
    pitch_shift_for_transform,
    pad_octave_for_transform,
    echo_should_include_note,
    counter_skip_step,
)
from cadence.music.style_archetype import infer_composition_archetype_with_reason


def test_pitch_shift_varies_by_transform():
    a = pitch_shift_for_transform("sparse", 0)
    b = pitch_shift_for_transform("climax", 0)
    c = pitch_shift_for_transform("climax", 1)
    assert a != b
    assert b != c
    print("✓ test_pitch_shift_varies_by_transform OK")


def test_pad_octave_sparse_lower():
    assert pad_octave_for_transform("sparse", "reflection") < pad_octave_for_transform(
        "climax", "climax",
    )
    print("✓ test_pad_octave_sparse_lower OK")


def test_echo_subsamples_dense_melody():
    assert not echo_should_include_note(
        1, melody_notes_in_section=120, echo_notes_in_section=0, section_max_echo=80,
    )
    assert echo_should_include_note(
        0, melody_notes_in_section=120, echo_notes_in_section=0, section_max_echo=80,
    )
    print("✓ test_echo_subsamples_dense_melody OK")


def test_bedded_counter_thins_steps():
    assert counter_skip_step(1, "introduce", texture_mode="bedded", events_per_bar=8)
    assert not counter_skip_step(0, "introduce", texture_mode="bedded", events_per_bar=8)
    print("✓ test_bedded_counter_thins_steps OK")


def test_game_boss_orchestral_tags_win():
    d = infer_composition_archetype_with_reason(
        raw_prompt="boss fight combat épico",
        use_case="game",
        energy_level=5,
        style_profile=None,
    )
    # tags would come from profile in real pipeline
    from cadence.schemas.song_state import MusicalStyleProfile
    d2 = infer_composition_archetype_with_reason(
        raw_prompt="cinematic tension",
        use_case="game",
        energy_level=5,
        style_profile=MusicalStyleProfile(
            genres=["orchestral", "symphonic", "boss fight", "combat"],
            avoid=[],
            reasoning="",
        ),
    )
    assert d2.archetype == "orchestral_boss", d2.reason
    print(f"  archetype={d2.archetype} reason={d2.reason}")
    print("✓ test_game_boss_orchestral_tags_win OK")


if __name__ == "__main__":
    test_pitch_shift_varies_by_transform()
    test_pad_octave_sparse_lower()
    test_echo_subsamples_dense_melody()
    test_bedded_counter_thins_steps()
    test_game_boss_orchestral_tags_win()
    print("\n✓ All layer_voice_variation tests passed")
