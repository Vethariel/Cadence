"""Tests de coherencia narrativa mínima."""

from cadence.schemas.song_state import (
    NarrativeContract,
    NarrativeAnchors,
    SectionIntent,
    SongStructure,
    RhythmEvent,
    Track,
)
from cadence.music.narrative_validation import (
    check_global_motif_continuity,
    check_narrative_intensity_direction,
    check_narrative_key_section_coverage,
)


def _intent(sid: str, density: float, role: str = "establish") -> SectionIntent:
    return SectionIntent(
        id=sid,
        narrative_role=role,
        emotional_target="x",
        density=density,
        harmonic_tension=0.5,
        rhythmic_complexity=0.5,
        transition_out="cut",
    )


def _note(t: int, section: str, pitch: int = 60, velocity: int = 90) -> RhythmEvent:
    return RhythmEvent(
        t=t, type="note", pitch=pitch, duration_ms=200,
        velocity=velocity, beat_index=0, section=section,
    )


def test_key_section_coverage_fails_when_silent():
    contract = NarrativeContract(
        section_ids=["intro", "drop"],
        arc_type="rise",
        global_motif=[0, 2, 4],
        prompt_intent_signature="x",
    )
    anchors = NarrativeAnchors(
        arc_type="rise",
        global_motif=[0, 2, 4],
        section_ids=["intro", "drop"],
        key_section_ids=["drop"],
    )
    intent_map = {
        "intro": _intent("intro", 0.3),
        "drop": _intent("drop", 1.0, "climax"),
    }
    structure = SongStructure(
        sections=["intro", "drop"],
        bars_per_section={"intro": 4, "drop": 8},
        total_bars=12,
        estimated_duration_ms=20000,
    )
    tracks = [
        Track(id="melody", instrument="L", role="lead", events=[
            _note(i * 300, "intro") for i in range(10)
        ]),
    ]
    ok, msg = check_narrative_key_section_coverage(
        tracks, structure, contract, anchors, intent_map,
    )
    assert not ok
    assert "drop" in msg


def test_intensity_direction_climax_above_intro():
    contract = NarrativeContract(
        section_ids=["intro", "drop"],
        arc_type="rise",
        global_motif=[0, 2],
        prompt_intent_signature="x",
    )
    intent_map = {
        "intro": _intent("intro", 0.25, "establish"),
        "drop": _intent("drop", 0.95, "climax"),
    }
    flat = [
        Track(id="melody", instrument="L", role="lead", events=[
            _note(i * 200, "intro", velocity=80) for i in range(15)
        ] + [
            _note(4000 + i * 200, "drop", velocity=78) for i in range(15)
        ]),
    ]
    ok, _ = check_narrative_intensity_direction(
        flat, ["intro", "drop"], intent_map, contract,
    )
    assert not ok

    strong = [
        Track(id="melody", instrument="L", role="lead", events=[
            _note(i * 200, "intro", velocity=70) for i in range(15)
        ] + [
            _note(4000 + i * 200, "drop", velocity=105) for i in range(15)
        ]),
    ]
    ok2, _ = check_narrative_intensity_direction(
        strong, ["intro", "drop"], intent_map, contract,
    )
    assert ok2


def test_motif_continuity_soft_threshold():
    contract = NarrativeContract(
        section_ids=["drop"],
        arc_type="x",
        global_motif=[0, 2, 4],
        prompt_intent_signature="y",
    )
    anchors = NarrativeAnchors(
        arc_type="x",
        key_section_ids=["drop"],
        section_ids=["drop"],
    )
    intent_map = {"drop": _intent("drop", 0.9, "climax")}
    # C minor: 0,2,4 -> C, D, E (60,62,64)
    on_motif = [
        Track(id="melody", instrument="L", role="lead", events=[
            _note(i * 100, "drop", pitch=60 + (i % 3) * 2) for i in range(20)
        ]),
    ]
    ok, _ = check_global_motif_continuity(
        on_motif, contract, anchors, intent_map, key="C", mode="minor",
    )
    assert ok


if __name__ == "__main__":
    test_key_section_coverage_fails_when_silent()
    test_intensity_direction_climax_above_intro()
    test_motif_continuity_soft_threshold()
    print("All narrative_validation tests passed.")
