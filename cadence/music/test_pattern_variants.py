"""Sub-variantes de patrón y aliases de compatibilidad."""

from cadence.music.arp_patterns import build_arp_pitch_sequence, resolve_arp_pattern
from cadence.music.instrument_patterns import stab_steps
from cadence.music.strategy_pools import (
    DRUM_PATTERN_ALIASES,
    get_bass_pattern,
    get_drum_pattern,
)


def test_drum_alias_resolves_to_variant():
    a = get_drum_pattern("techno")
    b = get_drum_pattern("techno_a")
    assert a == b
    c = get_drum_pattern("techno_b")
    assert a["hihat"] != c["hihat"]


def test_bass_alias_and_variants_differ():
    a = get_bass_pattern("driving")
    b = get_bass_pattern("driving_b")
    assert a != b
    assert DRUM_PATTERN_ALIASES["techno"] == "techno_a"


def test_stab_variants_differ():
    sa = stab_steps("offbeat_a", 0)
    sb = stab_steps("offbeat_b", 0)
    assert sa != sb
    assert stab_steps("offbeat", 0) == sa


def test_arp_alias_and_variant_pitch():
    assert resolve_arp_pattern("up", 0) == "up_a"
    pa = build_arp_pitch_sequence([60, 64, 67], "up_a")
    pb = build_arp_pitch_sequence([60, 64, 67], "up_b")
    assert pa != pb


def test_pool_cardinality():
    from cadence.music.strategy_pools import BASS_POOL, DRUM_POOL
    from cadence.music.arp_patterns import ARP_PATTERNS
    from cadence.music.instrument_patterns import STAB_PATTERN_POOL

    assert len(DRUM_POOL) >= 16
    assert len(BASS_POOL) >= 16
    assert len(ARP_PATTERNS) >= 20
    assert len(STAB_PATTERN_POOL) >= 16


if __name__ == "__main__":
    test_drum_alias_resolves_to_variant()
    test_bass_alias_and_variants_differ()
    test_stab_variants_differ()
    test_arp_alias_and_variant_pitch()
    test_pool_cardinality()
    print("All pattern_variants tests passed.")
