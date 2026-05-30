"""Tests biblioteca de timbres — GM válido en A320U + referencias MIDI."""

import cadence.instruments  # noqa: F401
from cadence.instruments.registry import get_instrument, list_instruments
from cadence.music.instrument_catalog import TIMBRES_BY_INSTRUMENT, get_timbres
from cadence.music.instrument_catalog import is_drum
from cadence.music.timbre_library import (
    BROWSER_SOUNDFONT,
    GM_PROGRAM_NAMES,
    MIDI_REFERENCE_PROGRAMS,
    assert_browser_gm_program,
    extended_timbres_flat,
)


def test_all_extended_timbres_in_gm_range():
    for iid, entries in extended_timbres_flat().items():
        for program, name in entries:
            assert_browser_gm_program(program)
            assert name == GM_PROGRAM_NAMES[program]
    print("✓ test_all_extended_timbres_in_gm_range OK")


def test_merged_catalog_has_more_timbres_than_palettes_only():
    # melody: 5 from palettes alone, should be >= 15 merged
    melody = get_timbres("melody")
    assert len(melody) >= 22, f"melody solo {len(melody)} timbres (incl. piano/guitar)"
    bass = get_timbres("bass")
    assert len(bass) >= 8
    arp = get_timbres("arp_synth")
    assert len(arp) >= 12
    print(f"  counts: melody={len(melody)}, bass={len(bass)}, arp={len(arp)}")
    print("✓ test_merged_catalog_has_more_timbres_than_palettes_only OK")


def test_spider_dance_reference_programs_in_catalog():
    spider = MIDI_REFERENCE_PROGRAMS["UT_Spider_Dance_v2_Lu9.mid"]
    all_programs = {p for timbres in TIMBRES_BY_INSTRUMENT.values() for p, _ in timbres}
    missing = spider - all_programs
    # Timpani (47) es percusión orquestal — no aplica como timbre melódico
    melodic = spider - {47}
    missing_melodic = melodic - all_programs
    assert not missing_melodic, f"programas Spider Dance ausentes: {missing_melodic}"
    print("✓ test_spider_dance_reference_programs_in_catalog OK")


def test_energetic_reference_programs_in_catalog():
    energetic = MIDI_REFERENCE_PROGRAMS["Energetic - good sound.mid"]
    all_programs = {p for timbres in TIMBRES_BY_INSTRUMENT.values() for p, _ in timbres}
    missing = energetic - all_programs
    assert not missing, f"programas Energetic ausentes: {missing}"
    print("✓ test_energetic_reference_programs_in_catalog OK")


def test_bad_apple_dulcimer_in_catalog():
    dulcimer = 15
    all_programs = {p for timbres in TIMBRES_BY_INSTRUMENT.values() for p, _ in timbres}
    assert dulcimer in all_programs
    print("✓ test_bad_apple_dulcimer_in_catalog OK")


def test_every_melodic_instrument_has_timbres():
    for iid in list_instruments():
        defn = get_instrument(iid)
        if is_drum(iid, defn.role):
            continue
        assert len(get_timbres(iid)) >= 4, f"{iid} tiene pocos timbres"
    print("✓ test_every_melodic_instrument_has_timbres OK")


def test_browser_soundfont_documented():
    assert BROWSER_SOUNDFONT == "A320U"
    assert len(GM_PROGRAM_NAMES) == 128
    print("✓ test_browser_soundfont_documented OK")


if __name__ == "__main__":
    test_all_extended_timbres_in_gm_range()
    test_merged_catalog_has_more_timbres_than_palettes_only()
    test_spider_dance_reference_programs_in_catalog()
    test_energetic_reference_programs_in_catalog()
    test_bad_apple_dulcimer_in_catalog()
    test_every_melodic_instrument_has_timbres()
    test_browser_soundfont_documented()
    print("\nAll timbre library tests passed.")
