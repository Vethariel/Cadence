"""Schedule alineado con capas explícitas del arrangement."""

from cadence.music.layer_schedule import (
    LayerSchedule,
    LayerScheduleEntry,
    active_layers_at_bar,
    build_layer_schedule,
    sync_schedule_with_layer_specs,
)
from cadence.schemas.song_state import LayerSpec, SectionIntent, SongStructure


def _sparse_loop_structure() -> SongStructure:
    return SongStructure(
        sections=["intro", "pad_layering", "melodic_motif", "outro_loop"],
        bars_per_section={
            "intro": 4,
            "pad_layering": 4,
            "melodic_motif": 4,
            "outro_loop": 4,
        },
        total_bars=16,
        estimated_duration_ms=45714,
    )


def _sparse_intent_map() -> dict:
    return {
        "intro": SectionIntent(
            id="intro", narrative_role="establish", emotional_target="calm",
            density=0.35, harmonic_tension=0.25, rhythmic_complexity=0.3,
        ),
        "pad_layering": SectionIntent(
            id="pad_layering", narrative_role="establish", emotional_target="calm",
            density=0.35, harmonic_tension=0.25, rhythmic_complexity=0.2,
        ),
        "melodic_motif": SectionIntent(
            id="melodic_motif", narrative_role="establish", emotional_target="hopeful",
            density=0.45, harmonic_tension=0.35, rhythmic_complexity=0.3,
        ),
        "outro_loop": SectionIntent(
            id="outro_loop", narrative_role="release", emotional_target="stable",
            density=0.3, harmonic_tension=0.2, rhythmic_complexity=0.35,
        ),
    }


def test_sync_schedule_adds_chord_stab_for_explicit_sections():
    structure = _sparse_loop_structure()
    layers = [
        LayerSpec(
            instrument_id="bass", role="bass", active_sections=["*"],
            pattern_strategy="loop_1bar", mix_level=-6.0, min_density=0.0,
        ),
        LayerSpec(
            instrument_id="melody", role="lead", active_sections=["*"],
            pattern_strategy="phrase_4bar", mix_level=-8.0, min_density=0.2,
        ),
        LayerSpec(
            instrument_id="pad", role="pad",
            active_sections=["intro", "pad_layering", "melodic_motif", "outro_loop"],
            pattern_strategy="chord_sustain", mix_level=-14.0, min_density=0.25,
        ),
        LayerSpec(
            instrument_id="chord_stab", role="lead", active_sections=["melodic_motif"],
            pattern_strategy="loop_1bar", mix_level=-13.0, min_density=0.45,
        ),
    ]
    schedule = build_layer_schedule(
        structure,
        [l.instrument_id for l in layers],
        _sparse_intent_map(),
        energy_level=2,
        use_case="loop",
        composition_archetype="ambient_loop",
    )
    assert not any("chord_stab" in e.add for e in schedule.entries)

    synced = sync_schedule_with_layer_specs(structure, layers, schedule)
    adds = [(e.bar, e.add) for e in synced.entries if "chord_stab" in e.add]
    assert adds, "chord_stab debe programarse en melodic_motif"
    motif_start = 8  # intro 4 + pad_layering 4
    assert any(bar == motif_start + 1 for bar, _ in adds)


def test_active_layers_at_bar_includes_synced_chord_stab():
    structure = _sparse_loop_structure()
    layers = [
        LayerSpec(
            instrument_id="chord_stab", role="lead", active_sections=["melodic_motif"],
            pattern_strategy="loop_1bar", mix_level=-13.0, min_density=0.45,
        ),
    ]
    schedule = LayerSchedule(
        entries=[LayerScheduleEntry(bar=9, add=["chord_stab"], remove=[])],
        core_layers=["bass", "melody", "pad"],
    )
    available = {"bass", "melody", "pad", "chord_stab"}
    active = active_layers_at_bar(schedule, 9, available)
    assert "chord_stab" in active


if __name__ == "__main__":
    test_sync_schedule_adds_chord_stab_for_explicit_sections()
    test_active_layers_at_bar_includes_synced_chord_stab()
    print("✓ layer_schedule_sync tests passed")
