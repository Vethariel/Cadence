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
        # chiptune / Spider Dance
        (6, "Harpsichord", "chiptune,dance"),
        (79, "Ocarina", "chiptune,dance"),
        (82, "Lead Calliope", "chiptune,synth"),
        (83, "Lead Chiff", "chiptune,synth"),
        (84, "Lead Charang", "dubstep,synth"),
        # touhou / Bad Apple
        (4, "Electric Piano 1", "cinematic,dance"),
        (5, "Electric Piano 2", "cinematic,dance"),
        (11, "Vibraphone", "cinematic,ambient"),
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
}


# Timbres ancla por estilo (ex-PALETTES) — genre-defaults en el catálogo
STYLE_PALETTES: dict[str, dict[str, tuple[int, str]]] = {
    "chiptune": {
        "melody": (80, "Lead Square"),
        "countermelody": (81, "Lead Saw"),
        "echo_synth": (80, "Lead Square"),
        "arp_synth": (12, "Marimba"),
        "bass": (39, "Synth Bass 2"),
        "pad": (88, "Pad New Age"),
        "chord_stab": (81, "Lead Saw"),
        "perc_aux": (115, "Melodic Tom"),
        "fx_riser": (119, "Reverse Cymbal"),
    },
    "techno_industrial": {
        "melody": (81, "Lead Saw"),
        "countermelody": (82, "Lead Calliope"),
        "echo_synth": (87, "Lead 8va"),
        "arp_synth": (98, "Crystal"),
        "bass": (38, "Synth Bass 1"),
        "pad": (89, "Pad Warm"),
        "chord_stab": (62, "Synth Brass"),
        "perc_aux": (116, "Synth Drum"),
        "fx_riser": (119, "Reverse Cymbal"),
    },
    "ambient_cinematic": {
        "melody": (88, "Pad Voice"),
        "countermelody": (53, "Voice Oohs"),
        "echo_synth": (92, "Space Voice"),
        "arp_synth": (14, "Tubular Bells"),
        "bass": (32, "Acoustic Bass"),
        "pad": (89, "Pad Warm"),
        "chord_stab": (48, "String Ensemble"),
        "perc_aux": (117, "Taiko Drum"),
        "fx_riser": (95, "Pad Sweep"),
    },
    "orchestral_game": {
        "melody": (48, "String Ensemble"),
        "countermelody": (53, "Voice Oohs"),
        "echo_synth": (50, "Synth Strings"),
        "arp_synth": (46, "Orchestral Harp"),
        "bass": (43, "Contrabass"),
        "pad": (49, "String Tremolo"),
        "chord_stab": (61, "Brass Section"),
        "perc_aux": (117, "Taiko Drum"),
        "fx_riser": (119, "Reverse Cymbal"),
    },
    "dance_game": {
        "melody": (7, "Clavi"),
        "countermelody": (81, "Lead Saw"),
        "echo_synth": (80, "Lead Square"),
        "arp_synth": (98, "Crystal"),
        "bass": (34, "Finger Bass"),
        "pad": (89, "Pad Warm"),
        "chord_stab": (62, "Synth Brass"),
        "perc_aux": (116, "Synth Drum"),
        "fx_riser": (119, "Reverse Cymbal"),
    },
    "dubstep_bass": {
        "melody": (87, "Lead 5th"),
        "countermelody": (38, "Synth Bass 1"),
        "echo_synth": (81, "Lead Saw"),
        "arp_synth": (38, "Synth Bass 1"),
        "bass": (39, "Synth Bass 2"),
        "pad": (95, "Pad Sweep"),
        "chord_stab": (62, "Synth Brass"),
        "perc_aux": (116, "Synth Drum"),
        "fx_riser": (119, "Reverse Cymbal"),
    },
}

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
