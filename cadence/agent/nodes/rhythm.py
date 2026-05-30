from cadence.schemas.song_state import (
    HarmonyPlan,
    SectionIntent,
    SongState,
    Track,
    RhythmEvent,
)
from cadence.agent.nodes.narrative_apply import (
    bar_variant_step,
    bass_should_play,
    drum_velocities,
    hihat_active,
    snare_ghost_velocity,
    transition_events,
)
from cadence.music.narrative_contract import section_intent_map_from_state
from cadence.music.harmony_theory import (
    chord_at_bar,
    chord_pitches,
    section_harmony_map,
)
from cadence.music.development_theory import section_development_map
from cadence.music.segment_variation import (
    pattern_id_for_segment,
    segment_at_bar,
    segment_index_at_bar,
)
from cadence.music.strategy_pools import BASS_POOL, DRUM_POOL, get_bass_pattern, get_drum_pattern


# ── Patrones de batería por estilo ────────────────────────────
# Patrones definidos en strategy_pools.py — aquí solo MIDI y velocidades.

DRUM_MIDI = {"kick": 36, "snare": 38, "hihat": 42, "clap": 39}

# Velocidades por sección para dar dinámica
SECTION_VELOCITY = {
    "intro":      {"kick": 70,  "snare": 60,  "hihat": 50},
    "build-up":   {"kick": 85,  "snare": 75,  "hihat": 65},
    "verse":      {"kick": 80,  "snare": 70,  "hihat": 60},
    "chorus":     {"kick": 110, "snare": 100, "hihat": 80},
    "drop":       {"kick": 127, "snare": 110, "hihat": 90},
    "breakdown":  {"kick": 60,  "snare": 50,  "hihat": 40},
    "climax":     {"kick": 127, "snare": 120, "hihat": 100},
    "outro":      {"kick": 70,  "snare": 60,  "hihat": 50},
    "default":    {"kick": 90,  "snare": 80,  "hihat": 70},
}

# Notas de bajo por modo (intervalos desde la tónica en semitonos)
BASS_INTERVALS = {
    "minor": [0, 0, 3, 0,  5, 0, 7, 0,  0, 0, 3, 0,  7, 0, 5, 0],
    "major": [0, 0, 4, 0,  5, 0, 7, 0,  0, 0, 4, 0,  7, 0, 5, 0],
}

# MIDI root notes por tonalidad
KEY_MIDI_ROOT = {
    "C": 36, "C#": 37, "D": 38, "D#": 39, "E": 40, "F": 41,
    "F#": 42, "G": 43, "G#": 44, "A": 45, "A#": 46, "B": 47,
}


# ── Helpers ───────────────────────────────────────────────────

def _ms_per_step(bpm: int, beats_per_bar: int = 4) -> float:
    """Duración en ms de un step de 1/16."""
    ms_per_beat = 60000 / bpm
    return ms_per_beat / 4


def _select_pattern(genre_tags: list[str], drum_pattern_id: str | None = None) -> dict:
    if drum_pattern_id:
        return get_drum_pattern(drum_pattern_id)
    for tag in genre_tags:
        tag_lower = tag.lower()
        pattern = get_drum_pattern(tag_lower)
        if tag_lower in ("techno", "dubstep", "house", "breakbeat", "default"):
            return pattern
    return get_drum_pattern("default")


def _get_root_midi(key: str) -> int:
    key_clean = key.split()[0].capitalize()
    return KEY_MIDI_ROOT.get(key_clean, 36)


# ── Generadores ───────────────────────────────────────────────

def _generate_drum_track(
    sections: list[str],
    bars_per_section: dict[str, int],
    bpm: int,
    genre_tags: list[str],
    intent_map: dict[str, SectionIntent] | None = None,
    drum_pattern_id: str | None = None,
    *,
    development=None,
    generation_seed: int = 0,
) -> Track:
    base_pattern_id = drum_pattern_id or "default"
    base_pattern = _select_pattern(genre_tags, base_pattern_id)
    dev_map = section_development_map(development)
    step_ms = _ms_per_step(bpm)
    steps_per_bar = 16
    events = []
    beat_index = 0
    current_t = 0
    intent_map = intent_map or {}

    for section in sections:
        bars = bars_per_section.get(section, 4)
        intent = intent_map.get(section)
        velocities = drum_velocities(section, intent, SECTION_VELOCITY)
        sec_dev = dev_map.get(section)

        for bar_idx in range(bars):
            pattern = base_pattern
            if sec_dev and sec_dev.segments:
                seg = segment_at_bar(sec_dev, bar_idx)
                seg_idx = segment_index_at_bar(sec_dev, bar_idx)
                pid = pattern_id_for_segment(
                    base_pattern_id,
                    seg_idx,
                    seg.transform if seg else sec_dev.transform,
                    generation_seed + hash(section) % 9973,
                    DRUM_POOL,
                )
                pattern = get_drum_pattern(pid)
            is_last_bar = bar_idx == bars - 1
            transition_out = (
                intent.transition_out
                if intent and is_last_bar and intent.transition_out != "none"
                else "none"
            )
            max_step = 8 if transition_out == "cut" else steps_per_bar

            for step in range(max_step):
                eff_step = bar_variant_step(step, bar_idx, intent)
                for drum_name, drum_pattern in pattern.items():
                    if drum_pattern[eff_step] != 1:
                        continue
                    if drum_name == "hihat" and not hihat_active(eff_step, intent):
                        continue
                    events.append(RhythmEvent(
                        t=int(current_t + step * step_ms),
                        type="drum_hit",
                        pitch=DRUM_MIDI.get(drum_name, 36),
                        duration_ms=int(step_ms * 0.9),
                        velocity=velocities.get(drum_name, 80),
                        beat_index=beat_index + step,
                        section=section,
                    ))
                    ghost = snare_ghost_velocity(
                        velocities.get("snare", 80), eff_step, intent,
                    )
                    if drum_name == "snare" and ghost is not None:
                        events.append(RhythmEvent(
                            t=int(current_t + step * step_ms),
                            type="drum_hit",
                            pitch=DRUM_MIDI["snare"],
                            duration_ms=int(step_ms * 0.5),
                            velocity=ghost,
                            beat_index=beat_index + step,
                            section=section,
                        ))

            if transition_out not in ("none", "cut"):
                events.extend(transition_events(
                    t_bar_start=current_t,
                    step_ms=step_ms,
                    transition_out=transition_out,
                    section=section,
                    beat_index=beat_index,
                    drum_midi=DRUM_MIDI,
                ))

            current_t += steps_per_bar * step_ms
            beat_index += steps_per_bar

    return Track(
        id="drums",
        instrument="Drum Kit",
        midi_channel=9,
        role="rhythm",
        events=events,
    )


def _generate_bass_track(
    sections: list[str],
    bars_per_section: dict[str, int],
    bpm: int,
    key: str,
    mode: str,
    intent_map: dict[str, SectionIntent] | None = None,
    harmony: HarmonyPlan | None = None,
    bass_pattern_id: str | None = None,
    *,
    development=None,
    generation_seed: int = 0,
) -> Track:
    step_ms = _ms_per_step(bpm)
    steps_per_bar = 16
    root_midi = _get_root_midi(key)
    intervals = BASS_INTERVALS.get(mode, BASS_INTERVALS["minor"])
    events = []
    beat_index = 0
    current_t = 0
    intent_map = intent_map or {}
    harmony_map = section_harmony_map(harmony)
    base_bass_id = bass_pattern_id or "root_fifth"
    dev_map = section_development_map(development)

    for section in sections:
        bars = bars_per_section.get(section, 4)
        intent = intent_map.get(section)

        if not bass_should_play(section, intent):
            current_t += bars * steps_per_bar * step_ms
            beat_index += bars * steps_per_bar
            continue

        density = intent.density if intent else 0.7
        base_vel = int(55 + density * 45)
        section_h = harmony_map.get(section)
        sec_dev = dev_map.get(section)

        for bar_idx in range(bars):
            octave_shift = 12 if bar_idx % 2 == 1 and (intent and intent.rhythmic_complexity >= 0.5) else 0
            bass_steps = get_bass_pattern(base_bass_id)
            if sec_dev and sec_dev.segments:
                seg = segment_at_bar(sec_dev, bar_idx)
                seg_idx = segment_index_at_bar(sec_dev, bar_idx)
                pid = pattern_id_for_segment(
                    base_bass_id,
                    seg_idx,
                    seg.transform if seg else sec_dev.transform,
                    generation_seed + hash(section) % 9973 + 3,
                    BASS_POOL,
                )
                bass_steps = get_bass_pattern(pid)

            if section_h:
                chord = chord_at_bar(section_h, bar_idx)
                tones = chord_pitches(key, mode, chord, octave=2)
                root_pitch = tones[0]
                fifth_pitch = tones[2] if len(tones) > 2 else root_pitch + 7
                for step, role in bass_steps:
                    pitch = root_pitch if role == "root" else fifth_pitch
                    vel = base_vel if step % 4 == 0 else max(45, base_vel - 15)
                    events.append(RhythmEvent(
                        t=int(current_t + step * step_ms),
                        type="note",
                        pitch=pitch + octave_shift,
                        duration_ms=int(step_ms * 1.8),
                        velocity=vel,
                        beat_index=beat_index + step,
                        section=section,
                    ))
            else:
                for step in range(steps_per_bar):
                    interval = intervals[step % len(intervals)]
                    if interval > 0 or step % 4 == 0:
                        vel = base_vel if step % 4 == 0 else max(45, base_vel - 20)
                        events.append(RhythmEvent(
                            t=int(current_t + step * step_ms),
                            type="note",
                            pitch=root_midi + interval + octave_shift,
                            duration_ms=int(step_ms * 1.8),
                            velocity=vel,
                            beat_index=beat_index + step,
                            section=section,
                        ))

            current_t += steps_per_bar * step_ms
            beat_index += steps_per_bar

    return Track(
        id="bass",
        instrument="Bass Synth",
        midi_channel=1,
        role="bass",
        events=events,
    )


# ── Nodo ─────────────────────────────────────────────────────

def rhythm_engine_node(state: SongState) -> dict:
    """
    Genera los tracks de drums y bass de forma determinista
    basándose en los parámetros técnicos y la estructura.
    """
    intent = state["intent"]
    proposal = state.get("technical_proposal")
    structure = state["structure"]

    # Resolver parámetros desde proposal o desde intent
    if proposal:
        bpm = proposal.bpm
        key = proposal.key
        mode = proposal.mode
        genre_tags = proposal.genre_tags
    else:
        bpm = 120
        key = "C"
        mode = "minor"
        genre_tags = intent.style_tags

    harmony = state.get("harmony")
    strategies = state.get("strategies")
    development = state.get("development")
    intent_map = section_intent_map_from_state(state, context="rhythm_engine")
    gen_seed = state.get("generation_seed", 0)

    drums = _generate_drum_track(
        sections=structure.sections,
        bars_per_section=structure.bars_per_section,
        bpm=bpm,
        genre_tags=genre_tags,
        intent_map=intent_map,
        drum_pattern_id=strategies.drum_pattern if strategies else None,
        development=development,
        generation_seed=gen_seed,
    )

    bass = _generate_bass_track(
        sections=structure.sections,
        bars_per_section=structure.bars_per_section,
        bpm=bpm,
        key=key,
        mode=mode,
        intent_map=intent_map,
        harmony=harmony,
        bass_pattern_id=strategies.bass_pattern if strategies else None,
        development=development,
        generation_seed=gen_seed,
    )

    existing = [t for t in state.get("tracks", []) if t.id not in ("drums", "bass")]
    return {"tracks": existing + [drums, bass]}
