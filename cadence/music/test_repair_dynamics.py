"""Tests de reparación de dinámica en post_process."""

from cadence.schemas.song_state import SongStructure, Track, RhythmEvent, SectionIntent
from cadence.music.repair_dynamics import (
    apply_repair_dynamic_range,
    apply_repair_intensity_arc,
)


def _note(t, section, velocity=80):
    return RhythmEvent(
        t=t, type="note", pitch=60, duration_ms=200,
        velocity=velocity, beat_index=0, section=section,
    )


def test_repair_dynamic_increases_spread():
    structure = SongStructure(
        sections=["intro", "drop"],
        bars_per_section={"intro": 4, "drop": 8},
        total_bars=12,
        estimated_duration_ms=24000,
    )
    intent_map = {
        "intro": SectionIntent(
            id="intro", narrative_role="establish", emotional_target="x",
            density=0.3, harmonic_tension=0.2, rhythmic_complexity=0.3,
            transition_out="cut",
        ),
        "drop": SectionIntent(
            id="drop", narrative_role="climax", emotional_target="x",
            density=1.0, harmonic_tension=0.8, rhythmic_complexity=0.7,
            transition_out="cut",
        ),
    }
    tracks = [
        Track(id="melody", instrument="L", role="lead", events=[
            _note(i * 200, "intro", 82) for i in range(10)
        ] + [
            _note(3000 + i * 200, "drop", 84) for i in range(10)
        ]),
    ]
    out = apply_repair_dynamic_range(tracks, structure, 120, intent_map)
    intro_avg = sum(e.velocity for e in out[0].events if e.section == "intro") / 10
    drop_avg = sum(e.velocity for e in out[0].events if e.section == "drop") / 10
    assert drop_avg - intro_avg >= 8


def test_repair_intensity_boosts_climax():
    structure = SongStructure(
        sections=["intro", "drop"],
        bars_per_section={"intro": 4, "drop": 8},
        total_bars=12,
        estimated_duration_ms=24000,
    )
    intent_map = {
        "intro": SectionIntent(
            id="intro", narrative_role="establish", emotional_target="x",
            density=0.25, harmonic_tension=0.2, rhythmic_complexity=0.3,
            transition_out="cut",
        ),
        "drop": SectionIntent(
            id="drop", narrative_role="climax", emotional_target="x",
            density=0.95, harmonic_tension=0.8, rhythmic_complexity=0.7,
            transition_out="cut",
        ),
    }
    tracks = [
        Track(id="melody", instrument="L", role="lead", events=[
            _note(i * 200, "intro", 90) for i in range(8)
        ] + [
            _note(3000 + i * 200, "drop", 85) for i in range(8)
        ]),
    ]
    out = apply_repair_intensity_arc(tracks, structure, 120, intent_map)
    drop_avg = sum(e.velocity for e in out[0].events if e.section == "drop") / 8
    intro_avg = sum(e.velocity for e in out[0].events if e.section == "intro") / 8
    assert drop_avg > intro_avg


if __name__ == "__main__":
    test_repair_dynamic_increases_spread()
    test_repair_intensity_boosts_climax()
    print("All repair_dynamics tests passed.")
