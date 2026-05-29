from cadence.schemas.song_state import SongState, Track, RhythmEvent


# ── Patrones de batería por estilo ────────────────────────────
# Cada patrón es una lista de 16 steps (1/16 de compás en 4/4)
# 1 = golpe, 0 = silencio
# kick=36, snare=38, hihat=42, clap=39 (números MIDI GM)

DRUM_PATTERNS = {
    "techno": {
        "kick":  [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
        "snare": [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        "hihat": [1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0],
    },
    "dubstep": {
        "kick":  [1,0,0,0, 0,0,1,0, 1,0,0,0, 0,0,0,0],
        "snare": [0,0,0,0, 1,0,0,1, 0,0,0,0, 1,0,1,0],
        "hihat": [1,1,0,1, 1,1,0,1, 1,1,0,1, 1,1,0,1],
    },
    "default": {
        "kick":  [1,0,0,0, 0,0,1,0, 1,0,0,0, 0,0,1,0],
        "snare": [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        "hihat": [1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0],
    },
}

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


def _select_pattern(genre_tags: list[str]) -> dict:
    for tag in genre_tags:
        tag_lower = tag.lower()
        for key in DRUM_PATTERNS:
            if key in tag_lower:
                return DRUM_PATTERNS[key]
    return DRUM_PATTERNS["default"]


def _get_root_midi(key: str) -> int:
    key_clean = key.split()[0].capitalize()
    return KEY_MIDI_ROOT.get(key_clean, 36)


# ── Generadores ───────────────────────────────────────────────

def _generate_drum_track(
    sections: list[str],
    bars_per_section: dict[str, int],
    bpm: int,
    genre_tags: list[str],
) -> Track:
    pattern = _select_pattern(genre_tags)
    step_ms = _ms_per_step(bpm)
    steps_per_bar = 16
    events = []
    beat_index = 0
    current_t = 0

    for section in sections:
        bars = bars_per_section.get(section, 4)
        velocities = SECTION_VELOCITY.get(section, SECTION_VELOCITY["default"])

        for _ in range(bars):
            for step in range(steps_per_bar):
                for drum_name, drum_pattern in pattern.items():
                    if drum_pattern[step] == 1:
                        events.append(RhythmEvent(
                            t=int(current_t + step * step_ms),
                            type="drum_hit",
                            pitch=DRUM_MIDI.get(drum_name, 36),
                            duration_ms=int(step_ms * 0.9),
                            velocity=velocities.get(drum_name, 80),
                            beat_index=beat_index + step,
                            section=section,
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
) -> Track:
    step_ms = _ms_per_step(bpm)
    steps_per_bar = 16
    root_midi = _get_root_midi(key)
    intervals = BASS_INTERVALS.get(mode, BASS_INTERVALS["minor"])
    events = []
    beat_index = 0
    current_t = 0

    for section in sections:
        # En breakdown el bajo descansa
        if section == "breakdown":
            bars = bars_per_section.get(section, 4)
            current_t += bars * steps_per_bar * step_ms
            beat_index += bars * steps_per_bar
            continue

        bars = bars_per_section.get(section, 4)
        for _ in range(bars):
            for step in range(steps_per_bar):
                interval = intervals[step % len(intervals)]
                if interval > 0 or step % 4 == 0:
                    events.append(RhythmEvent(
                        t=int(current_t + step * step_ms),
                        type="note",
                        pitch=root_midi + interval,
                        duration_ms=int(step_ms * 1.8),
                        velocity=90 if step % 4 == 0 else 70,
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
        # Ruta técnica: valores por defecto razonables
        # (en paso posterior el intent parser los extraerá del prompt)
        bpm = 120
        key = "C"
        mode = "minor"
        genre_tags = intent.style_tags

    drums = _generate_drum_track(
        sections=structure.sections,
        bars_per_section=structure.bars_per_section,
        bpm=bpm,
        genre_tags=genre_tags,
    )

    bass = _generate_bass_track(
        sections=structure.sections,
        bars_per_section=structure.bars_per_section,
        bpm=bpm,
        key=key,
        mode=mode,
    )

    return {"tracks": [drums, bass]}
