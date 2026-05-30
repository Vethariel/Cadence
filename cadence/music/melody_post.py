"""Post-proceso determinista de melodía — densidad, silencios, saltos y registro."""

from __future__ import annotations

from collections import defaultdict

from cadence.agent.nodes.melody import _get_scale_pitches
from cadence.agent.nodes.narrative_apply import melody_rest_ratio, section_intent_map
from cadence.schemas.song_state import RhythmEvent, SongState, Track

MELODY_PITCH_MIN = 60   # C4
MELODY_PITCH_MAX = 84   # C6
MAX_LEAP_DEFAULT = 4
MAX_LEAP_HIGH_ENERGY = 7
MAX_LEAP_CLIMAX = 7
MIN_NOTES_PER_BAR_DENSE = 6
DENSE_SECTION_IDS = frozenset({"drop", "climax", "build-up", "chorus"})
DENSE_DENSITY = 0.7
FILL_VELOCITY = 72


def ms_per_bar(bpm: int) -> float:
    return (60000 / max(bpm, 1)) * 4


def ms_per_step(bpm: int) -> float:
    return (60000 / max(bpm, 1)) / 4


def _is_dense_section(section: str, intent_map: dict) -> bool:
    if section in DENSE_SECTION_IDS:
        return True
    intent = intent_map.get(section)
    return intent is not None and intent.density >= DENSE_DENSITY


def _nearest_scale_pitch(pitch: int, scale_pitches: list[int]) -> int:
    candidates = scale_pitches + [p + 12 for p in scale_pitches] + [p - 12 for p in scale_pitches]
    return min(candidates, key=lambda p: abs(p - pitch))


def _clamp_pitch(pitch: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, pitch))


def clamp_melody_register(events: list[RhythmEvent]) -> list[RhythmEvent]:
    return [
        e.model_copy(update={"pitch": _clamp_pitch(e.pitch, MELODY_PITCH_MIN, MELODY_PITCH_MAX)})
        for e in events
    ]


def _max_leap_semitones(
    section: str,
    climax_sections: set[str],
    energy_level: int,
    use_case: str = "game",
) -> int:
    uc = (use_case or "game").lower()
    if uc == "cutscene":
        return MAX_LEAP_DEFAULT
    if uc == "loop":
        return 5
    if section in climax_sections:
        return MAX_LEAP_CLIMAX
    if energy_level >= 5:
        return MAX_LEAP_HIGH_ENERGY
    if energy_level >= 4:
        return 6
    return MAX_LEAP_DEFAULT


def limit_melody_leaps(
    events: list[RhythmEvent],
    scale_pitches: list[int],
    climax_sections: set[str],
    energy_level: int = 3,
    use_case: str = "game",
) -> list[RhythmEvent]:
    if len(events) < 2:
        return events

    sorted_events = sorted(events, key=lambda e: e.t)
    result = [sorted_events[0]]

    for event in sorted_events[1:]:
        prev = result[-1]
        max_leap = _max_leap_semitones(
            event.section, climax_sections, energy_level, use_case,
        )
        delta = event.pitch - prev.pitch
        if abs(delta) <= max_leap:
            result.append(event)
            continue

        direction = 1 if delta > 0 else -1
        target = prev.pitch + direction * max_leap
        new_pitch = _nearest_scale_pitch(target, scale_pitches)
        new_pitch = _clamp_pitch(new_pitch, MELODY_PITCH_MIN, MELODY_PITCH_MAX)
        result.append(event.model_copy(update={"pitch": new_pitch}))

    return result


def _gap_ms(prev: RhythmEvent, nxt: RhythmEvent) -> float:
    return max(0.0, nxt.t - (prev.t + prev.duration_ms))


def fill_melody_gaps(
    events: list[RhythmEvent],
    bpm: int,
    scale_pitches: list[int],
    intent_map: dict,
    gap_threshold_ms: float | None = None,
) -> list[RhythmEvent]:
    """Inserta notas de paso en huecos grandes para bajar el rest ratio."""
    if len(events) < 2:
        return events

    step_ms = ms_per_step(bpm)
    if gap_threshold_ms is None:
        gap_threshold_ms = step_ms * 4  # ~1/4 de negra en steps 16th

    sorted_events = sorted(events, key=lambda e: e.t)
    filled: list[RhythmEvent] = [sorted_events[0]]

    for nxt in sorted_events[1:]:
        prev = filled[-1]
        gap = _gap_ms(prev, nxt)
        intent = intent_map.get(prev.section)
        max_ratio = melody_rest_ratio(intent)
        # Umbral más estricto en secciones densas
        threshold = gap_threshold_ms
        if _is_dense_section(prev.section, intent_map):
            threshold = step_ms * 2

        if gap >= threshold:
            # Solo rellenar si el hueco supera lo permitido para la sección
            bar_ms = ms_per_bar(bpm)
            approx_rest_ratio = gap / max(bar_ms, 1)
            if approx_rest_ratio > max_ratio * 0.5:
                mid_t = int(prev.t + prev.duration_ms + gap * 0.35)
                mid_pitch = (prev.pitch + nxt.pitch) // 2
                mid_pitch = _nearest_scale_pitch(mid_pitch, scale_pitches)
                mid_pitch = _clamp_pitch(mid_pitch, MELODY_PITCH_MIN, MELODY_PITCH_MAX)
                dur = int(min(gap * 0.55, step_ms * 2))
                filled.append(RhythmEvent(
                    t=mid_t,
                    type="note",
                    pitch=mid_pitch,
                    duration_ms=max(40, dur),
                    velocity=FILL_VELOCITY,
                    beat_index=prev.beat_index,
                    section=prev.section,
                ))

        filled.append(nxt)

    return sorted(filled, key=lambda e: e.t)


def densify_melody(
    events: list[RhythmEvent],
    bpm: int,
    scale_pitches: list[int],
    intent_map: dict,
    min_notes_per_bar: int = MIN_NOTES_PER_BAR_DENSE,
) -> list[RhythmEvent]:
    """Añade notas ornamentales en compases sparse de secciones densas."""
    if not events:
        return events

    bar_ms = ms_per_bar(bpm)
    step_ms = ms_per_step(bpm)
    by_bar: dict[tuple[str, int], list[RhythmEvent]] = defaultdict(list)

    for event in events:
        bar = int(event.t // bar_ms)
        by_bar[(event.section, bar)].append(event)

    extra: list[RhythmEvent] = []

    for (section, bar), bar_events in by_bar.items():
        if not _is_dense_section(section, intent_map):
            continue
        if len(bar_events) >= min_notes_per_bar:
            continue

        bar_start = bar * bar_ms
        pitches = [e.pitch for e in sorted(bar_events, key=lambda e: e.t)]
        ref_pitch = pitches[0] if pitches else scale_pitches[0]
        needed = min_notes_per_bar - len(bar_events)
        offbeat_steps = (2, 6, 10, 14)

        for i in range(needed):
            step = offbeat_steps[i % len(offbeat_steps)]
            t = int(bar_start + step * step_ms)
            if any(abs(e.t - t) < step_ms * 0.5 for e in bar_events):
                continue
            degree_pitch = scale_pitches[i % len(scale_pitches)]
            pitch = _clamp_pitch(
                (ref_pitch + degree_pitch) // 2 if pitches else degree_pitch,
                MELODY_PITCH_MIN,
                MELODY_PITCH_MAX,
            )
            extra.append(RhythmEvent(
                t=t,
                type="note",
                pitch=pitch,
                duration_ms=int(step_ms * 1.5),
                velocity=FILL_VELOCITY - 4,
                beat_index=bar * 16 + step,
                section=section,
            ))

    return sorted(events + extra, key=lambda e: e.t)


def _should_densify(
    intent_map: dict,
    use_case: str,
    melody_texture: str = "balanced",
    energy_level: int = 3,
) -> bool:
    if melody_texture in ("dense", "percussive"):
        return True
    if melody_texture == "sparse":
        return False
    if energy_level >= 4 and use_case == "game":
        return True
    if use_case in ("loop", "cutscene") and melody_texture != "dense":
        return False
    return energy_level >= 3 and use_case == "game"


def _should_fill_gaps(intent_map: dict, use_case: str, melody_texture: str = "balanced") -> bool:
    if melody_texture == "sparse":
        return False
    if use_case == "loop":
        return False
    if use_case == "cutscene" and melody_texture != "percussive":
        return False
    return True


def _min_notes_per_bar(use_case: str, energy: int, melody_texture: str = "balanced") -> int:
    if melody_texture == "sparse":
        return 2
    if melody_texture in ("dense", "percussive"):
        if energy >= 5:
            return 8
        return 6 if energy >= 4 else 5
    if use_case == "cutscene":
        return 3
    if energy >= 5:
        return 6
    if energy >= 4:
        return 5
    return 4


def process_melody_events(
    events: list[RhythmEvent],
    *,
    bpm: int,
    key: str,
    mode: str,
    intent_map: dict,
    use_case: str = "game",
    energy_level: int = 3,
    melody_texture: str = "balanced",
) -> list[RhythmEvent]:
    """Pipeline de post-proceso melódico — respeta silencios según estilo."""
    if not events:
        return events

    scale_pitches = _get_scale_pitches(key, mode)
    climax_sections = {
        sid for sid, intent in intent_map.items()
        if intent.narrative_role in ("climax", "tension") or intent.density >= DENSE_DENSITY
    }

    if _should_densify(intent_map, use_case, melody_texture, energy_level):
        events = densify_melody(
            events, bpm, scale_pitches, intent_map,
            min_notes_per_bar=_min_notes_per_bar(use_case, energy_level, melody_texture),
        )
    if _should_fill_gaps(intent_map, use_case, melody_texture):
        events = fill_melody_gaps(events, bpm, scale_pitches, intent_map)

    events = limit_melody_leaps(
        events, scale_pitches, climax_sections, energy_level, use_case,
    )
    events = clamp_melody_register(events)
    return sorted(events, key=lambda e: e.t)


def _maybe_quantize_to_harmony(
    events: list[RhythmEvent],
    state: SongState,
    *,
    bpm: int,
    key: str,
    mode: str,
) -> list[RhythmEvent]:
    from cadence.music.harmonic_coherence import (
        active_instrument_ids_from_plan,
        count_harmonic_support_layers,
        quantize_melody_events_to_harmony,
        should_quantize_melody_to_chords,
    )

    proposal = state.get("technical_proposal")
    structure = state.get("structure")
    harmony = state.get("harmony")
    intent = state.get("intent")
    plan = state.get("orchestration_plan")
    if not proposal or not structure or not harmony:
        return events

    energy = proposal.energy_level
    use_case = intent.use_case if intent else "game"
    active = active_instrument_ids_from_plan(plan)
    if not should_quantize_melody_to_chords(
        count_harmonic_support_layers(active), energy, use_case,
    ):
        return events

    return quantize_melody_events_to_harmony(
        events,
        harmony=harmony,
        structure_sections=structure.sections,
        bars_per_section=structure.bars_per_section,
        key=key,
        mode=mode,
        bpm=bpm,
    )


def process_melody_track(track: Track, state: SongState) -> Track:
    proposal = state.get("technical_proposal")
    intent = state["intent"]
    bpm = proposal.bpm if proposal else 120
    key = proposal.key if proposal else "C"
    mode = proposal.mode if proposal else "minor"
    energy = proposal.energy_level if proposal else 3
    intent_map = section_intent_map(state.get("narrative"))
    from cadence.music.repertoire_signals import default_melody_texture

    orch = state.get("orchestration_plan")
    requested = orch.melody_texture if orch else "balanced"
    melody_texture = default_melody_texture(energy, intent.use_case, requested)

    events = process_melody_events(
        track.events,
        bpm=bpm,
        key=key,
        mode=mode,
        intent_map=intent_map,
        use_case=intent.use_case,
        energy_level=energy,
        melody_texture=melody_texture,
    )
    events = _maybe_quantize_to_harmony(events, state, bpm=bpm, key=key, mode=mode)
    return track.model_copy(update={"events": events})


def apply_melody_post(tracks: list[Track], state: SongState) -> list[Track]:
    """Aplica post-proceso melódico al track lead."""
    result = []
    for track in tracks:
        if track.id == "melody" and track.events:
            result.append(process_melody_track(track, state))
        else:
            result.append(track)
    return result
