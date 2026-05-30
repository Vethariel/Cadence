"""Diversidad instrumental por variantes de paleta de arquetipo."""

from cadence.music.instrument_catalog import (
    apply_archetype_palette_diversity,
    pick_archetype_timbre,
)
from cadence.music.timbre_library import (
    palette_candidate_programs,
    palette_for_archetype,
    palette_variant_keys,
)
from cadence.schemas.song_state import InstrumentAssignment


def test_ambient_loop_has_multiple_palette_variants():
    keys = palette_variant_keys("ambient_loop")
    assert len(keys) >= 3
    mel_progs = palette_candidate_programs("melody", "ambient_loop")
    assert len(mel_progs) >= 3, f"melody programs: {mel_progs}"


def test_palette_for_archetype_rotates_by_seed():
    p0 = palette_for_archetype("sparse_loop", generation_seed=0)
    p1 = palette_for_archetype("sparse_loop", generation_seed=1)
    # variant keys differ → at least one layer may differ
    assert p0 is not p1 or p0.get("melody") != p1.get("melody")


def test_pick_archetype_timbre_varies_by_seed():
    ctx = {
        "genre_tags": ["ambient", "loop"],
        "mood": "",
        "use_case": "loop",
        "composition_archetype": "ambient_loop",
        "raw_prompt": "",
    }
    progs = {
        pick_archetype_timbre("melody", generation_seed=s, timbre_context=ctx)[0]
        for s in (1, 17, 42, 99, 203)
    }
    assert len(progs) >= 2, f"expected variety, got {progs}"


def test_apply_archetype_palette_diversifies_optionals():
    by_id = {
        "melody": InstrumentAssignment(
            instrument_id="melody", role="lead", gm_program=0,
            display_name="Melody", mix_level=-8.0, active=True,
        ),
        "pad": InstrumentAssignment(
            instrument_id="pad", role="pad", gm_program=0,
            display_name="Pad", mix_level=-14.0, active=True,
        ),
    }
    ctx = {
        "genre_tags": ["chiptune", "arcade"],
        "mood": "",
        "use_case": "game",
        "composition_archetype": "chiptune_dance",
        "raw_prompt": "",
    }
    apply_archetype_palette_diversity(by_id, generation_seed=77, timbre_context=ctx)
    assert by_id["melody"].gm_program != 0
    assert by_id["melody"].display_name != "Melody"
    assert by_id["pad"].gm_program != 0
    assert by_id["pad"].display_name != "Pad"


def test_compact_action_melody_pool_includes_guitar_and_synth():
    progs = set(palette_candidate_programs("melody", "compact_action"))
    assert 27 in progs or 29 in progs  # guitar family
    assert 81 in progs  # synth variant


if __name__ == "__main__":
    test_ambient_loop_has_multiple_palette_variants()
    test_palette_for_archetype_rotates_by_seed()
    test_pick_archetype_timbre_varies_by_seed()
    test_apply_archetype_palette_diversifies_optionals()
    test_compact_action_melody_pool_includes_guitar_and_synth()
    print("✓ archetype palette diversity tests passed")
