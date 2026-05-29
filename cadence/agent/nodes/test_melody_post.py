"""Tests PR B — post-proceso melódico determinista."""

from cadence.agent.nodes.narrative_apply import section_intent_map
from cadence.music.melody_post import (
    MELODY_PITCH_MAX,
    MELODY_PITCH_MIN,
    clamp_melody_register,
    densify_melody,
    fill_melody_gaps,
    limit_melody_leaps,
    process_melody_events,
)
from cadence.schemas.song_state import RhythmEvent, SectionIntent, SongNarrative


def _intent_map(density: float = 1.0, role: str = "climax"):
    narrative = SongNarrative(
        logline="test",
        arc_type="test",
        sections=[
            SectionIntent(
                id="drop", narrative_role=role, emotional_target="triumph",
                density=density, harmonic_tension=0.8, rhythmic_complexity=0.7,
            ),
        ],
    )
    return section_intent_map(narrative)


def _note(t, pitch, section="drop", dur=200):
    return RhythmEvent(
        t=t, type="note", pitch=pitch, duration_ms=dur,
        velocity=80, beat_index=0, section=section,
    )


def test_clamp_melody_register():
    events = [_note(0, 48), _note(500, 90)]
    clamped = clamp_melody_register(events)
    assert clamped[0].pitch == MELODY_PITCH_MIN
    assert clamped[1].pitch == MELODY_PITCH_MAX
    print("✓ test_clamp_melody_register OK")


def test_limit_melody_leaps():
    scale = [60, 62, 63, 65, 67, 68, 70]
    events = [_note(0, 60), _note(500, 72)]  # leap 12 → should reduce
    limited = limit_melody_leaps(events, scale, {"drop"})
    assert abs(limited[1].pitch - limited[0].pitch) <= 7
    print("✓ test_limit_melody_leaps OK")


def test_densify_sparse_bar():
    intent_map = _intent_map()
    scale = [60, 62, 63, 65, 67, 68, 70]
    # 2 notas en compás 0 → debería añadir más en drop denso
    events = [_note(0, 65), _note(2000, 67)]
    densified = densify_melody(events, 120, scale, intent_map, min_notes_per_bar=6)
    bar0_notes = [e for e in densified if e.t < 2000]
    assert len(bar0_notes) >= 6, f"expected >=6 notes in bar 0, got {len(bar0_notes)}"
    print(f"  bar0 notes after densify: {len(bar0_notes)}")
    print("✓ test_densify_sparse_bar OK")


def test_fill_melody_gaps():
    intent_map = _intent_map()
    scale = [60, 62, 63, 65, 67, 68, 70]
    events = [_note(0, 60, dur=200), _note(2000, 67, dur=200)]
    filled = fill_melody_gaps(events, 120, scale, intent_map)
    assert len(filled) > len(events)
    print("✓ test_fill_melody_gaps OK")


def test_process_melody_pipeline():
    intent_map = _intent_map()
    events = [
        _note(0, 55),
        _note(800, 75),
        _note(3000, 67, dur=150),
    ]
    processed = process_melody_events(
        events, bpm=120, key="C", mode="minor", intent_map=intent_map,
    )
    assert all(MELODY_PITCH_MIN <= e.pitch <= MELODY_PITCH_MAX for e in processed)
    assert len(processed) >= len(events)
    print(f"  events: {len(events)} → {len(processed)}")
    print("✓ test_process_melody_pipeline OK")


if __name__ == "__main__":
    test_clamp_melody_register()
    test_limit_melody_leaps()
    test_densify_sparse_bar()
    test_fill_melody_gaps()
    test_process_melody_pipeline()
    print("\n✓ All melody post tests passed")
