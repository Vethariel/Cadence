"""Tests: modos modales y compases extendidos."""

from cadence.music.harmony_theory import scale_pitches, chord_pitches
from cadence.music.meter_theory import (
    beats_per_bar,
    ms_per_bar,
    normalize_time_signature,
    steps_per_bar,
)
from cadence.music.scale_theory import (
    harmony_template_key,
    normalize_mode,
    scale_semitones,
)
from cadence.schemas.song_state import TechnicalProposal


def test_normalize_mode_modal():
    assert normalize_mode("dorian") == "dorian"
    assert normalize_mode("frigio") == "phrygian"
    assert normalize_mode("Phrygian") == "phrygian"


def test_dorian_scale_differs_from_minor():
    minor = scale_semitones("minor")
    dorian = scale_semitones("dorian")
    assert minor != dorian
    assert dorian[5] == 9  # 6ª mayor


def test_harmony_uses_minor_templates_for_modal():
    assert harmony_template_key("dorian") == "minor"
    assert harmony_template_key("phrygian") == "minor"
    assert harmony_template_key("major") == "major"


def test_chord_pitches_respect_phrygian_scale():
    from cadence.schemas.song_state import ChordSpec

    pitches = chord_pitches("E", "phrygian", ChordSpec(root_degree=0, quality="minor", bars=1), octave=3)
    assert len(pitches) == 3
    assert pitches[1] - pitches[0] == 3  # minor third


def test_time_signature_3_4():
    ts = normalize_time_signature([3, 4])
    assert ts == [3, 4]
    assert beats_per_bar(ts) == 3
    assert steps_per_bar(ts) == 12
    assert ms_per_bar(120, ts) == 1500.0


def test_time_signature_6_8():
    ts = normalize_time_signature([6, 8])
    assert ts == [6, 8]
    assert beats_per_bar(ts) == 3
    assert steps_per_bar(ts) == 12


def test_technical_proposal_validates_mode_and_meter():
    p = TechnicalProposal(
        bpm=90,
        key="D",
        mode="dorian",
        time_signature=[5, 4],
        reasoning="t",
    )
    assert p.mode == "dorian"
    assert p.time_signature == [5, 4]


if __name__ == "__main__":
    test_normalize_mode_modal()
    test_dorian_scale_differs_from_minor()
    test_harmony_uses_minor_templates_for_modal()
    test_chord_pitches_respect_phrygian_scale()
    test_time_signature_3_4()
    test_time_signature_6_8()
    test_technical_proposal_validates_mode_and_meter()
    print("All scale_and_meter tests passed.")
