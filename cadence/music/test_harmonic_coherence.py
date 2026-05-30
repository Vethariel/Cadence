"""Tests de coherencia armónica en stacks densos."""

from cadence.music.harmonic_coherence import (
    apply_lead_support_cap,
    count_harmonic_support_layers,
    harmony_pool_for_dense_stack,
    quantize_melody_events_to_harmony,
    resolve_echo_source_for_stack,
    should_quantize_melody_to_chords,
)
from cadence.schemas.song_state import (
    ChordSpec,
    GenerationStrategies,
    HarmonyPlan,
    RhythmEvent,
    SectionHarmony,
)


def _minor_harmony():
    return HarmonyPlan(
        key="F",
        mode="minor",
        sections=[
            SectionHarmony(
                section_id="drop",
                progression=[
                    ChordSpec(root_degree=0, quality="minor", bars=4),
                ],
            ),
        ],
    )


def test_should_quantize_when_dense_stack():
    assert should_quantize_melody_to_chords(2, 5, "game")
    assert not should_quantize_melody_to_chords(1, 5, "game")
    assert not should_quantize_melody_to_chords(2, 3, "game")


def test_quantize_snaps_to_chord_tones():
    harm = _minor_harmony()
    # F minor chord tones around 65, 68, 72
    events = [
        RhythmEvent(
            t=0, type="note", pitch=70, duration_ms=100,
            velocity=80, beat_index=0, section="drop",
        ),
    ]
    out = quantize_melody_events_to_harmony(
        events,
        harmony=harm,
        structure_sections=["drop"],
        bars_per_section={"drop": 4},
        key="F",
        mode="minor",
        bpm=120,
    )
    assert out[0].pitch in (65, 68, 72, 77, 80, 84)


def test_harmony_pool_prefers_strategies_over_cinematic_agent():
    pool = harmony_pool_for_dense_stack(
        "cinematic", "aggressive", energy_level=5, use_case="game",
    )
    assert pool == "aggressive"


def test_echo_source_arp_when_dense_stack():
    active = {"arp_synth", "countermelody", "melody", "bass"}
    src = resolve_echo_source_for_stack(
        GenerationStrategies(generation_seed=1, echo_source="auto"),
        active,
        energy_level=5,
        use_case="game",
    )
    assert src == "arp_synth"


def test_lead_cap_keeps_arp_and_counter():
    active = {
        "melody", "arp_synth", "countermelody", "synth_pluck", "chord_stab", "echo_synth",
    }
    allowed = apply_lead_support_cap(active, energy_level=5, use_case="game")
    assert "melody" in allowed
    assert "arp_synth" in allowed
    assert "countermelody" in allowed
    assert "synth_pluck" not in allowed or "chord_stab" not in allowed


def test_count_harmonic_layers():
    assert count_harmonic_support_layers({"arp_synth", "bass"}) == 1
    assert count_harmonic_support_layers({"arp_synth", "countermelody"}) == 2


if __name__ == "__main__":
    test_should_quantize_when_dense_stack()
    test_quantize_snaps_to_chord_tones()
    test_harmony_pool_prefers_strategies_over_cinematic_agent()
    test_echo_source_arp_when_dense_stack()
    test_lead_cap_keeps_arp_and_counter()
    test_count_harmonic_layers()
    print("All harmonic coherence tests passed.")
