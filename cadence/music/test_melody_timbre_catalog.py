"""Catálogo de lead melody — piano, guitarra y filtros por estilo."""

import cadence.instruments  # noqa: F401
from cadence.music.instrument_catalog import TIMBRES_BY_INSTRUMENT, get_timbres
from cadence.music.timbre_library import (
    filter_melody_timbres,
    melody_catalog_has_piano_and_guitar,
    melody_timbre_allowed,
)


def test_melody_catalog_includes_piano_and_guitar():
    assert melody_catalog_has_piano_and_guitar()
    programs = {p for p, _ in get_timbres("melody")}
    assert 0 in programs, "Acoustic Grand Piano"
    assert 27 in programs, "Clean Electric Guitar"
    assert len(programs) >= 22
    print("✓ test_melody_catalog_includes_piano_and_guitar OK")


def test_ambient_loop_excludes_distortion_guitar_not_harmonics():
    all_mel = list(TIMBRES_BY_INSTRUMENT["melody"])
    filtered = filter_melody_timbres(
        all_mel,
        genre_tags=["ambient", "drone", "ethereal"],
        use_case="loop",
        composition_archetype="ambient_loop",
    )
    progs = {p for p, _ in filtered}
    assert 29 not in progs, "overdriven guitar fuera de loop etéreo"
    assert 27 not in progs
    assert 31 in progs or 0 in progs or 73 in progs


def test_chiptune_excludes_grand_piano():
    all_mel = list(TIMBRES_BY_INSTRUMENT["melody"])
    filtered = filter_melody_timbres(
        all_mel,
        genre_tags=["chiptune", "arcade"],
        use_case="game",
        composition_archetype="chiptune_dance",
    )
    progs = {p for p, _ in filtered}
    assert 0 not in progs
    assert 80 in progs or 82 in progs


def test_orchestral_prefers_strings_over_synth_lead():
    ctx = {"orchestral", "boss", "cinematic", "game"}
    assert not melody_timbre_allowed(81, "techno,synth", ctx)
    assert melody_timbre_allowed(40, "orchestral,boss", ctx)


if __name__ == "__main__":
    test_melody_catalog_includes_piano_and_guitar()
    test_ambient_loop_excludes_distortion_guitar_not_harmonics()
    test_chiptune_excludes_grand_piano()
    test_orchestral_prefers_strings_over_synth_lead()
    print("All melody_timbre_catalog tests passed.")
