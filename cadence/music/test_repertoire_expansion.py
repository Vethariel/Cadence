"""Tests de ampliación de repertorio (arp, harmony, patterns, synth_pluck)."""

from cadence.music.arp_patterns import ARP_PATTERNS, build_arp_pitch_sequence, resolve_arp_pattern
from cadence.music.instrument_patterns import (
    COUNTER_PATTERN_POOL,
    STAB_PATTERN_POOL,
    counter_steps,
    perc_clap_steps,
    pluck_steps,
    stab_steps,
)
from cadence.music.strategy_pools import HARMONY_POOL, get_harmony_templates, select_strategies
from cadence.instruments.registry import get_instrument, list_instruments


def test_arp_patterns_expanded():
    assert len(ARP_PATTERNS) >= 10
    assert "sixteenth" in ARP_PATTERNS
    seq = build_arp_pitch_sequence([48, 52, 55], "cascade")
    assert len(seq) >= 6
    assert resolve_arp_pattern("invalid", 42) in ARP_PATTERNS


def test_harmony_pools_expanded():
    assert "aggressive" in HARMONY_POOL
    assert "dark" in HARMONY_POOL
    tpl = get_harmony_templates("minor", "aggressive")
    assert "climax" in tpl and len(tpl["climax"]) >= 3


def test_instrument_pattern_pools():
    assert len(STAB_PATTERN_POOL) >= 9
    assert "sixteenth" in STAB_PATTERN_POOL
    assert "organ_offbeat" in STAB_PATTERN_POOL
    assert "orchestral_sync" in STAB_PATTERN_POOL
    assert stab_steps("four_on", 0) != stab_steps("sparse", 0)
    assert len(stab_steps("sixteenth", 0)) == 16
    assert len(pluck_steps("sixteenth", 0)) > len(pluck_steps("sparse", 0))
    assert len(COUNTER_PATTERN_POOL) >= 6
    assert counter_steps("offbeat_sync", 0) == (4, 6, 12, 14)


def test_strategies_include_layer_patterns():
    s = select_strategies(999, ["dubstep", "techno"], "minor", "game", 5)
    assert s.stab_pattern in STAB_PATTERN_POOL
    assert s.perc_pattern
    assert s.pluck_pattern
    assert s.counter_pattern in COUNTER_PATTERN_POOL
    assert s.echo_source in ("auto", "melody", "arp_synth", "chord_stab")


def test_dance_repertoire_bias_prefers_dense_patterns():
    s = select_strategies(42, ["boss fight", "techno"], "minor", "game", 5)
    assert s.arp_pattern in ("sixteenth", "cascade", "broken", "syncopated", "octave")
    assert s.harmony_pool in ("aggressive", "dance", "dark", "game", "classic", "modal", "cinematic")


def test_synth_pluck_registered():
    assert "synth_pluck" in list_instruments()
    assert get_instrument("synth_pluck").requires_llm is False


def test_format_layer_patterns_for_llm():
    from cadence.music.instrument_patterns import format_layer_patterns_for_llm
    text = format_layer_patterns_for_llm()
    assert "stab_pattern" in text
    assert "dubstep_off" in text
    assert "synth_pluck" in text


if __name__ == "__main__":
    test_arp_patterns_expanded()
    test_harmony_pools_expanded()
    test_instrument_pattern_pools()
    test_strategies_include_layer_patterns()
    test_dance_repertoire_bias_prefers_dense_patterns()
    test_synth_pluck_registered()
    test_format_layer_patterns_for_llm()
    print("All repertoire expansion tests passed.")
