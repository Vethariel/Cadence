"""Humanización determinista — micro-jitter en timing y velocity."""

import random

from cadence.schemas.song_state import RhythmEvent, Track

HUMANIZE_BY_ROLE: dict[str, dict[str, int]] = {
    "rhythm": {"t_ms": 12, "vel": 6},
    "bass": {"t_ms": 10, "vel": 5},
    "lead": {"t_ms": 18, "vel": 8},
    "pad": {"t_ms": 6, "vel": 4},
    "fx": {"t_ms": 0, "vel": 0},
}

SKIP_HUMANIZE_TYPES = frozenset({"chord"})


def _jitter(rng: random.Random, amount: int) -> int:
    if amount <= 0:
        return 0
    return rng.randint(-amount, amount)


def humanize_event(
    event: RhythmEvent,
    rng: random.Random,
    role: str,
) -> RhythmEvent:
    if event.type in SKIP_HUMANIZE_TYPES:
        return event

    cfg = HUMANIZE_BY_ROLE.get(role, HUMANIZE_BY_ROLE["lead"])
    t_delta = _jitter(rng, cfg["t_ms"])
    vel_delta = _jitter(rng, cfg["vel"])

    new_t = max(0, event.t + t_delta)
    new_vel = max(1, min(127, event.velocity + vel_delta))

    return event.model_copy(update={"t": new_t, "velocity": new_vel})


def humanize_track(track: Track, rng: random.Random) -> Track:
    events = [
        humanize_event(e, rng, track.role)
        for e in track.events
    ]
    events.sort(key=lambda e: (e.t, e.beat_index))
    return track.model_copy(update={"events": events})


def humanize_tracks(tracks: list[Track], generation_seed: int) -> list[Track]:
    rng = random.Random(generation_seed ^ 0xCAFE1234)
    return [humanize_track(t, rng) for t in tracks]
