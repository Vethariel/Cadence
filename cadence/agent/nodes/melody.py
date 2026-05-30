"""Tipos de fraseo melódico y composición determinista."""

from pydantic import BaseModel, Field

from cadence.schemas.song_state import SongState, Track
from cadence.music.melody_phrases import fix_phrase_steps
from cadence.music.meter_theory import ms_per_step as _meter_ms_per_step
from cadence.music.scale_theory import scale_pitches as _scale_pitches


class MelodyNote(BaseModel):
    scale_degree: int = Field(ge=0, le=6)
    octave_offset: int = Field(ge=-1, le=1, default=0)
    duration_steps: int = Field(ge=1, le=4)
    velocity: int = Field(ge=40, le=127)
    is_rest: bool = Field(default=False)


class MelodyPhrase(BaseModel):
    bars: int = Field(ge=2, le=4)
    pattern: list[MelodyNote] = Field(default_factory=list)


def _get_scale_pitches(key: str, mode: str) -> list[int]:
    return _scale_pitches(key, mode, octave=4)


def _ms_per_step(bpm: int, time_signature: list[int] | None = None) -> float:
    return _meter_ms_per_step(bpm, time_signature)


def _fix_section_phrases(
    phrases: list[MelodyPhrase],
    bar_steps: int = 16,
) -> list[MelodyPhrase]:
    fixed = []
    for phrase in phrases:
        total_steps = phrase.bars * bar_steps
        pattern = fix_phrase_steps(phrase.pattern, total_steps)
        fixed.append(phrase.model_copy(update={"pattern": pattern}))
    return fixed


def compose_melody_track(state: SongState) -> Track:
    """Genera melodía determinista desde motivo, desarrollo y armonía."""
    from cadence.music.melody_compose import compose_melody_deterministic

    return compose_melody_deterministic(state)


def melody_composer_node(state: SongState) -> dict:
    melody_track = compose_melody_track(state)
    existing_tracks = [t for t in state.get("tracks", []) if t.id != "melody"]
    return {"tracks": existing_tracks + [melody_track]}
