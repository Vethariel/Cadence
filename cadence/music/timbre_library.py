"""
Biblioteca extendida de timbres GM para Cadence.

Referencias MIDI en examples/:
  - UT_Spider_Dance_v2_Lu9.mid — harpsichord, brass, square/saw leads, finger bass, warm pad
  - Bad Apple!!.mid           — dulcimer, electric organ textures
  - Its_Pizza_Time.mid        — capas sparse / chiptune-adjacent
  - ASGORE.mid                — boss orquestal denso (strings, brass, choir)
  - MILF.mid                  — cutscene moderada

Reproducción navegador: cadence-ui/public/soundfonts/A320U.sf2 (GeneralUser GS).
Implementa General MIDI 1–128 (program 0–127) — todos los timbres aquí son válidos.
"""

from __future__ import annotations

# Nombres estándar GM (FluidR3 / General MIDI Level 1)
GM_PROGRAM_NAMES: dict[int, str] = {
    0: "Acoustic Grand Piano",
    1: "Bright Acoustic Piano",
    2: "Electric Grand Piano",
    3: "Honky-tonk Piano",
    4: "Electric Piano 1",
    5: "Electric Piano 2",
    6: "Harpsichord",
    7: "Clavinet",
    8: "Celesta",
    9: "Glockenspiel",
    10: "Music Box",
    11: "Vibraphone",
    12: "Marimba",
    13: "Xylophone",
    14: "Tubular Bells",
    15: "Dulcimer",
    16: "Drawbar Organ",
    17: "Percussive Organ",
    18: "Rock Organ",
    19: "Church Organ",
    20: "Reed Organ",
    21: "Accordion",
    22: "Harmonica",
    23: "Tango Accordion",
    24: "Nylon Guitar",
    25: "Steel Guitar",
    26: "Jazz Guitar",
    27: "Clean Guitar",
    28: "Muted Guitar",
    29: "Overdriven Guitar",
    30: "Distortion Guitar",
    31: "Guitar Harmonics",
    32: "Acoustic Bass",
    33: "Finger Bass",
    34: "Pick Bass",
    35: "Fretless Bass",
    36: "Slap Bass 1",
    37: "Slap Bass 2",
    38: "Synth Bass 1",
    39: "Synth Bass 2",
    40: "Violin",
    41: "Viola",
    42: "Cello",
    43: "Contrabass",
    44: "Tremolo Strings",
    45: "Pizzicato Strings",
    46: "Orchestral Harp",
    47: "Timpani",
    48: "String Ensemble 1",
    49: "String Tremolo",
    50: "Synth Strings 1",
    51: "Synth Strings 2",
    52: "Choir Aahs",
    53: "Voice Oohs",
    54: "Synth Voice",
    55: "Orchestra Hit",
    56: "Trumpet",
    57: "Trombone",
    58: "Tuba",
    59: "Muted Trumpet",
    60: "French Horn",
    61: "Brass Section",
    62: "Synth Brass 1",
    63: "Synth Brass 2",
    64: "Soprano Sax",
    65: "Alto Sax",
    66: "Tenor Sax",
    67: "Baritone Sax",
    68: "Oboe",
    69: "English Horn",
    70: "Bassoon",
    71: "Clarinet",
    72: "Piccolo",
    73: "Flute",
    74: "Recorder",
    75: "Pan Flute",
    76: "Blown Bottle",
    77: "Shakuhachi",
    78: "Whistle",
    79: "Ocarina",
    80: "Lead Square",
    81: "Lead Sawtooth",
    82: "Lead Calliope",
    83: "Lead Chiff",
    84: "Lead Charang",
    85: "Lead Voice",
    86: "Lead Fifths",
    87: "Lead Bass+Lead",
    88: "Pad New Age",
    89: "Pad Warm",
    90: "Pad Polysynth",
    91: "Pad Choir",
    92: "Pad Bowed",
    93: "Pad Metallic",
    94: "Halo Pad",
    95: "Pad Sweep",
    96: "FX Rain",
    97: "FX Soundtrack",
    98: "FX Crystal",
    99: "FX Atmosphere",
    100: "FX Brightness",
    101: "FX Goblins",
    102: "FX Echoes",
    103: "FX Sci-Fi",
    104: "Sitar",
    105: "Banjo",
    106: "Shamisen",
    107: "Koto",
    108: "Kalimba",
    109: "Bagpipe",
    110: "Fiddle",
    111: "Shanai",
    112: "Tinkle Bell",
    113: "Agogo",
    114: "Steel Drums",
    115: "Woodblock",
    116: "Taiko Drum",
    117: "Melodic Tom",
    118: "Synth Drum",
    119: "Reverse Cymbal",
    120: "Guitar Fret Noise",
    121: "Breath Noise",
    122: "Seashore",
    123: "Bird Tweet",
    124: "Telephone Ring",
    125: "Helicopter",
    126: "Applause",
    127: "Gunshot",
}

BROWSER_SOUNDFONT = "A320U"

# Timbres extra por instrument_id — (gm_program, nombre, estilos de referencia)
# Se fusionan con las paletas en instrument_catalog.TIMBRES_BY_INSTRUMENT
EXTENDED_TIMBRES: dict[str, list[tuple[int, str, str]]] = {
    "melody": [
        # piano — lead acústico/eléctrico
        (0, "Acoustic Grand Piano", "cinematic,cutscene,ambient"),
        (1, "Bright Acoustic Piano", "pop,cinematic,game"),
        (2, "Electric Grand Piano", "pop,dance,game"),
        (3, "Honky-tonk Piano", "retro,game,country"),
        (4, "Electric Piano 1", "cinematic,dance,pop,jazz"),
        (5, "Electric Piano 2", "cinematic,dance,pop,jazz"),
        # guitarra — lead (no ambient etéreo puro)
        (24, "Nylon Guitar", "folk,game,cutscene,pop"),
        (25, "Steel Guitar", "folk,country,cinematic"),
        (26, "Jazz Guitar", "jazz,cinematic,cutscene"),
        (27, "Clean Electric Guitar", "rock,pop,game,platform"),
        (28, "Muted Guitar", "funk,game,dance"),
        (29, "Overdriven Guitar", "rock,dubstep,game,metal"),
        (30, "Distortion Guitar", "rock,metal,game,boss"),
        (31, "Guitar Harmonics", "ambient,ethereal,cinematic"),
        # chiptune / Spider Dance
        (6, "Harpsichord", "chiptune,dance"),
        (79, "Ocarina", "chiptune,dance"),
        (82, "Lead Calliope", "chiptune,synth"),
        (83, "Lead Chiff", "chiptune,synth"),
        (84, "Lead Charang", "dubstep,synth"),
        (11, "Vibraphone", "cinematic,ambient,jazz"),
        (15, "Dulcimer", "cinematic,dance"),
        # boss / Asgore
        (40, "Violin", "orchestral,boss"),
        (52, "Choir Aahs", "orchestral,boss"),
        (56, "Trumpet", "orchestral,boss"),
        (73, "Flute", "orchestral,ambient"),
        (85, "Lead Voice", "ambient,cinematic"),
        (54, "Synth Voice", "ambient,synth"),
    ],
    "bass": [
        (33, "Finger Bass", "dance,chiptune"),   # Spider Dance Pick Bass
        (34, "Pick Bass", "rock,game"),
        (35, "Fretless Bass", "funk,cinematic"),
        (36, "Slap Bass 1", "funk,dance"),
        (37, "Slap Bass 2", "funk,dubstep"),
    ],
    "arp_synth": [
        (6, "Harpsichord", "chiptune,dance"),
        (9, "Glockenspiel", "cinematic,ambient"),
        (10, "Music Box", "chiptune,loop"),
        (11, "Vibraphone", "cinematic,jazz"),
        (15, "Dulcimer", "cinematic,dance"),
        (73, "Flute", "orchestral,ambient"),
        (76, "Blown Bottle", "ambient,ethereal"),
        (112, "Tinkle Bell", "chiptune,magic"),
    ],
    "echo_synth": [
        (6, "Harpsichord", "chiptune,dance"),
        (88, "Pad New Age", "ambient,loop"),
        (89, "Pad Warm", "ambient,cinematic"),
        (91, "Pad Choir", "orchestral,cinematic"),
        (99, "FX Atmosphere", "ambient,space"),
        (102, "FX Echoes", "cinematic,space"),
    ],
    "pad": [
        (48, "String Ensemble 1", "orchestral,cinematic"),
        (50, "Synth Strings 1", "orchestral,synth"),
        (52, "Choir Aahs", "orchestral,boss"),
        (90, "Pad Polysynth", "synth,techno"),
        (91, "Pad Choir", "orchestral,cinematic"),
        (92, "Pad Bowed", "ambient,dark"),
        (94, "Halo Pad", "ambient,ethereal"),
    ],
    "countermelody": [
        (48, "String Ensemble 1", "orchestral,boss"),
        (52, "Choir Aahs", "orchestral,cinematic"),
        (54, "Synth Voice", "ambient,synth"),
        (56, "Trumpet", "orchestral,boss"),
        (6, "Harpsichord", "chiptune,dance"),
        (73, "Flute", "orchestral,ambient"),
        (85, "Lead Voice", "ambient,cinematic"),
    ],
    "chord_stab": [
        (55, "Orchestra Hit", "orchestral,boss"),
        (56, "Trumpet", "orchestral,boss"),
        (63, "Synth Brass 2", "dubstep,synth"),
        (51, "Synth Strings 2", "cinematic,synth"),
        (29, "Overdriven Guitar", "rock,game"),
        (16, "Drawbar Organ", "retro,game"),
    ],
    "synth_pluck": [
        (25, "Acoustic Guitar (nylon)", "folk,game"),
        (27, "Electric Guitar (clean)", "pop,game"),
        (29, "Overdriven Guitar", "rock,dubstep"),
        (4, "Electric Piano 1", "pop,dance"),
        (81, "Lead Sawtooth", "techno,synth"),
        (87, "Lead 5th", "dubstep,synth"),
    ],
    "fx_riser": [
        (96, "FX Rain", "ambient,cinematic"),
        (97, "FX Soundtrack", "cinematic,boss"),
        (99, "FX Atmosphere", "ambient,space"),
        (100, "FX Brightness", "climax,boss"),
        (102, "FX Echoes", "cinematic,space"),
        (103, "FX Sci-Fi", "techno,space"),
    ],
    # Familias ensemble — varias maderas/teclas/guitarras en la misma pieza
    "woodwind_a": [
        (73, "Flute", "orchestral,ambient,cinematic"),
        (71, "Clarinet", "orchestral,jazz"),
        (68, "Oboe", "orchestral,cinematic"),
        (78, "Whistle", "folk,game"),
    ],
    "woodwind_b": [
        (72, "Piccolo", "orchestral,boss"),
        (73, "Flute", "orchestral,ambient"),
        (75, "Pan Flute", "folk,cinematic"),
        (79, "Ocarina", "chiptune,folk"),
    ],
    "keys_piano": [
        (0, "Acoustic Grand Piano", "cinematic,cutscene,folk"),
        (1, "Bright Acoustic Piano", "pop,cinematic,game"),
        (2, "Electric Grand Piano", "pop,dance,game"),
        (4, "Electric Piano 1", "jazz,cinematic,dance"),
        (5, "Electric Piano 2", "jazz,pop"),
    ],
    "keys_organ": [
        (16, "Drawbar Organ", "retro,game,rock"),
        (17, "Percussive Organ", "rock,game"),
        (18, "Rock Organ", "rock,boss"),
        (19, "Church Organ", "orchestral,cinematic,gothic"),
        (20, "Reed Organ", "folk,cinematic"),
    ],
    "strings_ensemble": [
        (48, "String Ensemble 1", "orchestral,cinematic"),
        (49, "String Tremolo", "orchestral,boss"),
        (44, "Tremolo Strings", "cinematic,boss"),
        (50, "Synth Strings 1", "orchestral,synth"),
        (52, "Choir Aahs", "orchestral,boss"),
    ],
    "guitar_acoustic": [
        (24, "Nylon Guitar", "folk,game,cutscene"),
        (25, "Steel Guitar", "folk,country,cinematic"),
        (26, "Jazz Guitar", "jazz,cinematic"),
        (31, "Guitar Harmonics", "ambient,cinematic,game"),
    ],
    "guitar_electric": [
        (27, "Clean Electric Guitar", "rock,pop,game"),
        (28, "Muted Guitar", "funk,dance"),
        (29, "Overdriven Guitar", "rock,metal,boss"),
        (30, "Distortion Guitar", "metal,boss"),
    ],
    "brass_a": [
        (56, "Trumpet", "orchestral,boss"),
        (57, "Trombone", "orchestral,jazz"),
        (60, "French Horn", "orchestral,cinematic"),
        (61, "Brass Section", "orchestral,boss"),
        (62, "Synth Brass 1", "dubstep,synth"),
    ],
}


# Timbres ancla por estilo (ex-PALETTES) — genre-defaults en el catálogo.
# echo_synth usa programa distinto a melody en cada paleta (evita duplicar el lead).
STYLE_PALETTES: dict[str, dict[str, tuple[int, str]]] = {
    "chiptune": {
        "melody": (80, "Lead Square"),
        "countermelody": (79, "Ocarina"),
        "echo_synth": (88, "Pad New Age"),
        "arp_synth": (10, "Music Box"),
        "bass": (33, "Finger Bass"),
        "pad": (89, "Pad Warm"),
        "chord_stab": (62, "Synth Brass 1"),
        "perc_aux": (115, "Melodic Tom"),
        "fx_riser": (119, "Reverse Cymbal"),
    },
    "chiptune_hybrid": {
        "melody": (6, "Harpsichord"),
        "countermelody": (4, "Electric Piano 1"),
        "echo_synth": (79, "Ocarina"),
        "arp_synth": (12, "Marimba"),
        "bass": (34, "Pick Bass"),
        "pad": (88, "Pad New Age"),
        "chord_stab": (15, "Dulcimer"),
        "perc_aux": (115, "Melodic Tom"),
        "fx_riser": (119, "Reverse Cymbal"),
    },
    "techno_industrial": {
        "melody": (81, "Lead Sawtooth"),
        "countermelody": (82, "Lead Calliope"),
        "echo_synth": (87, "Lead 5th"),
        "arp_synth": (98, "Crystal"),
        "bass": (38, "Synth Bass 1"),
        "pad": (89, "Pad Warm"),
        "chord_stab": (62, "Synth Brass 1"),
        "perc_aux": (116, "Synth Drum"),
        "fx_riser": (119, "Reverse Cymbal"),
    },
    "ambient_cinematic": {
        "melody": (0, "Acoustic Grand Piano"),
        "countermelody": (73, "Flute"),
        "echo_synth": (99, "FX Atmosphere"),
        "arp_synth": (14, "Tubular Bells"),
        "bass": (32, "Acoustic Bass"),
        "pad": (94, "Halo Pad"),
        "chord_stab": (48, "String Ensemble 1"),
        "perc_aux": (117, "Taiko Drum"),
        "fx_riser": (95, "Pad Sweep"),
    },
    "ambient_loop": {
        "melody": (4, "Electric Piano 1"),
        "countermelody": (54, "Synth Voice"),
        "echo_synth": (102, "FX Echoes"),
        "arp_synth": (9, "Glockenspiel"),
        "bass": (38, "Synth Bass 1"),
        "pad": (92, "Pad Bowed"),
        "chord_stab": (91, "Pad Choir"),
        "perc_aux": (117, "Taiko Drum"),
        "fx_riser": (99, "FX Atmosphere"),
    },
    "orchestral_game": {
        "melody": (48, "String Ensemble 1"),
        "countermelody": (73, "Flute"),
        "echo_synth": (46, "Orchestral Harp"),
        "arp_synth": (46, "Orchestral Harp"),
        "bass": (43, "Contrabass"),
        "pad": (49, "String Tremolo"),
        "chord_stab": (61, "Brass Section"),
        "perc_aux": (117, "Taiko Drum"),
        "fx_riser": (119, "Reverse Cymbal"),
    },
    "orchestral_boss": {
        "melody": (40, "Violin"),
        "countermelody": (52, "Choir Aahs"),
        "echo_synth": (50, "Synth Strings 1"),
        "arp_synth": (46, "Orchestral Harp"),
        "bass": (43, "Contrabass"),
        "pad": (48, "String Ensemble 1"),
        "chord_stab": (55, "Orchestra Hit"),
        "perc_aux": (117, "Taiko Drum"),
        "fx_riser": (100, "FX Brightness"),
    },
    "cinematic_cutscene": {
        "melody": (1, "Bright Acoustic Piano"),
        "countermelody": (73, "Flute"),
        "echo_synth": (92, "Space Voice"),
        "arp_synth": (11, "Vibraphone"),
        "bass": (32, "Acoustic Bass"),
        "pad": (94, "Halo Pad"),
        "chord_stab": (48, "String Ensemble 1"),
        "perc_aux": (117, "Taiko Drum"),
        "fx_riser": (95, "Pad Sweep"),
    },
    "dance_game": {
        "melody": (7, "Clavinet"),
        "countermelody": (27, "Clean Electric Guitar"),
        "echo_synth": (98, "Crystal"),
        "arp_synth": (98, "Crystal"),
        "bass": (34, "Finger Bass"),
        "pad": (89, "Pad Warm"),
        "chord_stab": (62, "Synth Brass 1"),
        "perc_aux": (116, "Synth Drum"),
        "fx_riser": (119, "Reverse Cymbal"),
    },
    "compact_action": {
        "melody": (27, "Clean Electric Guitar"),
        "countermelody": (40, "Violin"),
        "echo_synth": (102, "FX Echoes"),
        "arp_synth": (98, "Crystal"),
        "bass": (34, "Pick Bass"),
        "pad": (50, "Synth Strings 1"),
        "chord_stab": (56, "Trumpet"),
        "perc_aux": (116, "Synth Drum"),
        "fx_riser": (119, "Reverse Cymbal"),
    },
    "dubstep_bass": {
        "melody": (87, "Lead 5th"),
        "countermelody": (38, "Synth Bass 1"),
        "echo_synth": (103, "FX Sci-Fi"),
        "arp_synth": (38, "Synth Bass 1"),
        "bass": (39, "Synth Bass 2"),
        "pad": (95, "Pad Sweep"),
        "chord_stab": (62, "Synth Brass 1"),
        "perc_aux": (116, "Synth Drum"),
        "fx_riser": (119, "Reverse Cymbal"),
    },
}


def palette_echo_differs_from_melody(palette: dict[str, tuple[int, str]]) -> bool:
    """True si echo_synth no comparte gm_program con melody en una paleta ancla."""
    mel = palette.get("melody")
    echo = palette.get("echo_synth")
    if not mel or not echo:
        return True
    return mel[0] != echo[0]

# Programas vistos en MIDIs de referencia — deben estar en el catálogo final
MIDI_REFERENCE_PROGRAMS: dict[str, set[int]] = {
    "UT_Spider_Dance_v2_Lu9.mid": {6, 33, 47, 61, 79, 80, 88},
    "Bad Apple!!.mid": {15, 16},
    "Energetic - good sound.mid": {7, 34, 38, 48, 80, 81, 98},
    "MILF.mid": set(),
    "Its_Pizza_Time.mid": set(),
    "ASGORE.mid": set(),
}


def gm_name(program: int) -> str:
    return GM_PROGRAM_NAMES.get(program, f"GM {program}")


def assert_browser_gm_program(program: int) -> None:
    if program not in GM_PROGRAM_NAMES:
        raise ValueError(f"gm_program {program} fuera de GM 0–127 ({BROWSER_SOUNDFONT})")


def extended_timbres_flat() -> dict[str, list[tuple[int, str]]]:
    """Convierte EXTENDED_TIMBRES a (program, name) sin tags."""
    out: dict[str, list[tuple[int, str]]] = {}
    for iid, entries in EXTENDED_TIMBRES.items():
        out[iid] = [(p, gm_name(p)) for p, _n, _tags in entries]
    return out


# GM programs excluidos por contexto (coherencia de estilo)
_MELODY_EXCLUDE_GUITAR = frozenset(range(24, 31))  # 24–30; 31 harmonics permitido en ambient
_MELODY_EXCLUDE_PIANO = frozenset({0, 1, 2, 3})  # piano acústico fuera de chiptune puro
_MELODY_EXCLUDE_SYNTH_LEAD = frozenset({80, 81, 82, 83, 84, 87})  # fuera de orquesta/cutscene


def _context_tokens(
    genre_tags: list[str] | None,
    mood: str,
    use_case: str,
    composition_archetype: str | None,
) -> set[str]:
    tokens: set[str] = set()
    for t in genre_tags or []:
        for part in t.lower().replace(",", " ").split():
            if part:
                tokens.add(part)
    for part in (mood or "").lower().split():
        if part:
            tokens.add(part)
    tokens.add((use_case or "game").lower())
    if composition_archetype:
        tokens.add(composition_archetype.lower())
        if composition_archetype == "ambient_loop":
            tokens.update(("ambient", "loop", "ethereal"))
        elif composition_archetype == "cinematic_cutscene":
            tokens.update(("cinematic", "cutscene"))
        elif composition_archetype == "chiptune_dance":
            tokens.update(("chiptune", "dance", "synth"))
        elif composition_archetype == "orchestral_boss":
            tokens.update(("orchestral", "boss"))
    return tokens


def melody_timbre_allowed(
    program: int,
    style_tags: str,
    context_tokens: set[str],
) -> bool:
    """True si el timbre encaja con el contexto (tags del catálogo ∩ contexto)."""
    tag_set = {t.strip().lower() for t in style_tags.split(",") if t.strip()}
    if tag_set and not (tag_set & context_tokens):
        return False

    ethereal = context_tokens & {"ambient", "loop", "ethereal", "drone", "soundscape"}
    if program in _MELODY_EXCLUDE_GUITAR and ethereal:
        return program == 31  # harmonics sí en ambient

    if program in _MELODY_EXCLUDE_PIANO and context_tokens & {
        "chiptune", "eurobeat", "arcade", "8-bit", "8bit",
    }:
        return False

    orchestralish = context_tokens & {"orchestral", "boss", "cinematic", "cutscene"}
    if program in _MELODY_EXCLUDE_SYNTH_LEAD and orchestralish:
        if not (context_tokens & {"chiptune", "techno", "dubstep", "synth", "dance"}):
            return False

    return True


def bass_timbre_allowed(
    program: int,
    style_tags: str,
    context_tokens: set[str],
) -> bool:
    """True si el bajo encaja con el contexto (tags del catálogo ∩ contexto)."""
    tag_set = {t.strip().lower() for t in style_tags.split(",") if t.strip()}
    if tag_set and not (tag_set & context_tokens):
        return False

    orchestralish = context_tokens & {"orchestral", "boss", "cinematic", "cutscene", "epic"}
    synth_bass = program in (38, 39)
    if synth_bass and orchestralish:
        if not (context_tokens & {"chiptune", "techno", "dubstep", "dance", "synth", "eurobeat"}):
            return False

    slap = program in (36, 37)
    if slap and context_tokens & {"ambient", "loop", "ethereal", "drone"}:
        return False

    return True


def filter_bass_timbres(
    timbres: list[tuple[int, str]],
    *,
    genre_tags: list[str] | None = None,
    mood: str = "",
    use_case: str = "game",
    composition_archetype: str | None = None,
) -> list[tuple[int, str]]:
    """Filtra timbres de bass por estilo; mantiene al menos 3 opciones."""
    entries = EXTENDED_TIMBRES.get("bass", [])
    prog_tags = {p: tags for p, _n, tags in entries}
    ctx = _context_tokens(genre_tags, mood, use_case, composition_archetype)

    filtered = [
        (p, n) for p, n in timbres
        if bass_timbre_allowed(p, prog_tags.get(p, ""), ctx)
    ]
    if len(filtered) >= 3:
        return filtered
    return timbres


def filter_melody_timbres(
    timbres: list[tuple[int, str]],
    *,
    genre_tags: list[str] | None = None,
    mood: str = "",
    use_case: str = "game",
    composition_archetype: str | None = None,
) -> list[tuple[int, str]]:
    """Filtra timbres de melody por estilo; mantiene al menos 4 opciones."""
    entries = EXTENDED_TIMBRES.get("melody", [])
    prog_tags = {p: tags for p, _n, tags in entries}
    ctx = _context_tokens(genre_tags, mood, use_case, composition_archetype)

    filtered = [
        (p, n) for p, n in timbres
        if melody_timbre_allowed(p, prog_tags.get(p, ""), ctx)
    ]
    if len(filtered) >= 4:
        return filtered
    return timbres


def melody_catalog_has_piano_and_guitar() -> bool:
    """True si el catálogo fusionado incluye piano y guitarra como lead."""
    programs = {p for p, _ in extended_timbres_flat().get("melody", [])}
    has_piano = bool(programs & {0, 1, 2, 3, 4, 5})
    has_guitar = bool(programs & set(range(24, 31)))
    return has_piano and has_guitar


def style_anchor_timbres_flat() -> dict[str, list[tuple[int, str]]]:
    """Unión de STYLE_PALETTES con nombres GM canónicos."""
    by_id: dict[str, dict[int, str]] = {}
    for palette in STYLE_PALETTES.values():
        for iid, (program, _name) in palette.items():
            assert_browser_gm_program(program)
            by_id.setdefault(iid, {})[program] = gm_name(program)
    return {
        iid: sorted(opts.items(), key=lambda x: x[0])
        for iid, opts in by_id.items()
    }
