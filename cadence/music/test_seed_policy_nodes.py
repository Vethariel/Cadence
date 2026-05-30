"""Tests de subsemillas por nodo creativo."""

from cadence.music.instrument_patterns import stab_steps
from cadence.music.seed_policy import derive_node_seed, seed_for_state, NODE_SALTS
from cadence.schemas.song_state import NodeSeeds


def test_node_salts_include_instrument_composers():
    for node in (
        "arp_synth", "chord_stab", "countermelody", "perc_aux", "synth_pluck",
        "melody", "melody_post", "rhythm_engine",
    ):
        assert node in NODE_SALTS, f"falta salt para {node}"


def test_same_seed_same_stab_pattern():
    a = stab_steps("offbeat", 1001)
    b = stab_steps("offbeat", 1001)
    assert a == b


def test_different_seed_different_stab_pattern():
    patterns = {tuple(stab_steps(None, s)) for s in range(0, 32)}
    assert len(patterns) >= 2


def test_seed_for_state_from_node_seeds():
    state = {
        "generation_seed": 42,
        "node_seeds": NodeSeeds(
            generation_seed=42,
            seed_arp_synth=derive_node_seed(42, "arp_synth"),
        ),
    }
    assert seed_for_state(state, "arp_synth") == derive_node_seed(42, "arp_synth")


if __name__ == "__main__":
    test_node_salts_include_instrument_composers()
    test_same_seed_same_stab_pattern()
    test_different_seed_different_stab_pattern()
    test_seed_for_state_from_node_seeds()
    print("All seed_policy_nodes tests passed.")
