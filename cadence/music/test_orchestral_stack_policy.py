"""Política de stack orquestal — secciones exclusivas y rotación."""

from cadence.music.orchestral_stack_policy import (
    assign_orchestral_layer_sections,
    effective_texture_mode_for_schedule,
    rotating_support_for_section,
    segment_layer_delta_orchestral,
)
from cadence.schemas.song_state import SectionIntent, SongStructure


def _intent(role: str, density: float) -> SectionIntent:
    return SectionIntent(
        id="x",
        narrative_role=role,
        emotional_target="",
        density=density,
        harmonic_tension=0.5,
        rhythmic_complexity=0.5,
    )


def test_texture_staggered_not_simultaneous():
    mode = effective_texture_mode_for_schedule(
        "simultaneous",
        composition_archetype="orchestral_boss",
        energy_level=5,
    )
    assert mode == "staggered"


def test_rotating_counter_vs_arp():
    assert rotating_support_for_section(
        0, "climax", chosen={"countermelody", "arp_synth"},
    ) == "countermelody"
    assert rotating_support_for_section(
        1, "climax", chosen={"countermelody", "arp_synth"},
    ) == "arp_synth"


def test_section_layers_no_overlap():
    structure = SongStructure(
        sections=["intro", "climax_a", "climax_b"],
        bars_per_section={"intro": 8, "climax_a": 16, "climax_b": 16},
        total_bars=40,
        estimated_duration_ms=120000,
    )
    intent_map = {
        "intro": _intent("reflection", 0.3),
        "climax_a": _intent("climax", 0.85),
        "climax_b": _intent("climax", 0.9),
    }
    chosen = {"pad", "countermelody", "arp_synth", "chord_stab"}
    m = assign_orchestral_layer_sections(
        structure,
        intent_map,
        chosen,
        energy_level=5,
        pad_floor=0.2,
        stab_floor=0.4,
        counter_floor=0.5,
        arp_floor=0.55,
        echo_floor=0.55,
        perc_floor=0.5,
    )
    assert "intro" in m["pad"]
    assert "intro" not in m["countermelody"]
    assert "intro" not in m["arp_synth"]
    assert "climax_a" in m["countermelody"] or "climax_a" in m["arp_synth"]
    assert not (
        "climax_a" in m["countermelody"] and "climax_a" in m["arp_synth"]
    )


def test_segment_delta_sparse_removes_supports():
    remove, add = segment_layer_delta_orchestral(
        "sparse",
        available={"arp_synth", "countermelody", "pad"},
        segment_index=0,
        section_role="reflection",
    )
    assert "arp_synth" in remove
    assert "countermelody" in remove


if __name__ == "__main__":
    test_texture_staggered_not_simultaneous()
    test_rotating_counter_vs_arp()
    test_section_layers_no_overlap()
    test_segment_delta_sparse_removes_supports()
    print("All orchestral_stack_policy tests passed.")
