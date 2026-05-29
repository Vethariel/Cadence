"""Tests de métricas de riqueza y melody_post por energía."""

from cadence.music.melody_post import limit_melody_leaps, process_melody_events
from cadence.music.track_metrics import layers_active_stats, melody_leap_ratio
from cadence.schemas.song_state import RhythmEvent, Track


def _note(t, pitch, section="verse"):
    return RhythmEvent(
        t=t, type="note", pitch=pitch, duration_ms=200,
        velocity=80, beat_index=0, section=section,
    )


def test_high_energy_allows_wider_leaps():
    events = [_note(0, 60), _note(400, 67), _note(800, 72)]
    scale = [60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79, 81, 84]
    low = limit_melody_leaps(events, scale, {"drop"}, energy_level=2)
    high = limit_melody_leaps(events, scale, {"drop"}, energy_level=5)
    assert high[1].pitch == 67
    assert low[1].pitch == 64
    print("✓ test_high_energy_allows_wider_leaps OK")


def test_layers_active_stats():
    tracks = [
        Track(id="melody", instrument="m", role="lead", events=[_note(0, 72), _note(2000, 74)]),
        Track(id="bass", instrument="b", role="bass", events=[_note(0, 41), _note(2000, 43)]),
        Track(id="arp_synth", instrument="a", role="lead", events=[_note(0, 79), _note(2000, 76)]),
    ]
    mean, mx = layers_active_stats(tracks, 120)
    assert mean >= 2.0
    assert mx >= 2
    print(f"  layers mean={mean:.1f} max={mx}")
    print("✓ test_layers_active_stats OK")


def test_melody_leap_ratio():
    tracks = [
        Track(id="melody", instrument="m", role="lead", events=[
            _note(0, 60), _note(400, 72), _note(800, 84), _note(1200, 61),
        ]),
    ]
    ratio = melody_leap_ratio(tracks)
    assert ratio >= 0.5
    print("✓ test_melody_leap_ratio OK")


if __name__ == "__main__":
    test_high_energy_allows_wider_leaps()
    test_layers_active_stats()
    test_melody_leap_ratio()
    print("\n✓ All track metrics tests passed")
