"""Sub-variantes rítmicas (_a/_b) y aliases hacia IDs canónicos."""

from __future__ import annotations

# ── Batería: grids 16-step distintos por variante ──────────────

_DRUM_BASE: dict[str, dict[str, list[int]]] = {
    "techno": {
        "kick":  [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "hihat": [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    },
    "dubstep": {
        "kick":  [1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0],
        "hihat": [1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1],
    },
    "house": {
        "kick":  [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "hihat": [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0],
    },
    "breakbeat": {
        "kick":  [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0],
        "hihat": [1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0],
    },
    "halftime": {
        "kick":  [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "hihat": [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
    },
    "dnb": {
        "kick":  [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1],
        "hihat": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    },
    "industrial": {
        "kick":  [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "hihat": [1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1],
    },
    "default": {
        "kick":  [1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "hihat": [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    },
}

_DRUM_OVERRIDES_B: dict[str, dict[str, list[int]]] = {
    "techno": {
        "kick":  [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1],
        "hihat": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    },
    "house": {
        "kick":  [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
        "snare": [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0],
        "hihat": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
    },
    "breakbeat": {
        "kick":  [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0],
        "snare": [0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1],
        "hihat": [1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1],
    },
    "dubstep": {
        "kick":  [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0],
        "snare": [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1],
        "hihat": [0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1],
    },
    "halftime": {
        "kick":  [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        "snare": [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
        "hihat": [1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0],
    },
    "dnb": {
        "kick":  [1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1],
        "hihat": [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    },
    "industrial": {
        "kick":  [1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0],
        "snare": [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0],
        "hihat": [1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0],
    },
    "default": {
        "kick":  [1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0],
        "hihat": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
    },
}

def _build_drum_catalog() -> tuple[dict[str, dict[str, list[int]]], list[str], dict[str, str]]:
    patterns: dict[str, dict[str, list[int]]] = {}
    pool: list[str] = []
    aliases: dict[str, str] = {}
    for family, grid_a in _DRUM_BASE.items():
        cid_a = f"{family}_a"
        patterns[cid_a] = grid_a
        pool.append(cid_a)
        aliases[family] = cid_a
        grid_b = _DRUM_OVERRIDES_B.get(family, grid_a)
        cid_b = f"{family}_b"
        patterns[cid_b] = grid_b
        pool.append(cid_b)
    return patterns, pool, aliases


DRUM_VARIANT_PATTERNS, DRUM_VARIANT_POOL, DRUM_PATTERN_ALIASES = _build_drum_catalog()

# ── Bajo ───────────────────────────────────────────────────────

BassStep = tuple[int, str]

_BASS_BASE: dict[str, list[BassStep]] = {
    "root_fifth": [(0, "root"), (4, "root"), (8, "fifth"), (12, "root")],
    "driving": [(0, "root"), (3, "root"), (8, "fifth"), (11, "fifth")],
    "syncopated": [(2, "root"), (6, "fifth"), (10, "root"), (14, "fifth")],
    "pulse": [(0, "root"), (8, "root")],
    "half_time": [(0, "root"), (8, "root"), (12, "fifth")],
    "walk": [
        (0, "root"), (2, "root"), (4, "fifth"), (6, "root"),
        (8, "fifth"), (10, "root"), (12, "root"), (14, "fifth"),
    ],
    "octave_pulse": [(0, "root"), (4, "root"), (8, "root"), (12, "root")],
    "staccato": [(0, "root"), (4, "fifth"), (8, "root"), (12, "fifth")],
    "sub_drop": [(0, "root"), (14, "root")],
}

_BASS_VARIANT_B: dict[str, list[BassStep]] = {
    "root_fifth": [(0, "root"), (6, "fifth"), (8, "root"), (14, "fifth")],
    "driving": [(0, "root"), (5, "root"), (8, "fifth"), (13, "fifth")],
    "syncopated": [(1, "root"), (5, "fifth"), (9, "root"), (13, "fifth")],
    "pulse": [(0, "root"), (4, "root"), (8, "root"), (12, "root")],
    "half_time": [(0, "root"), (10, "fifth"), (12, "root")],
    "walk": [
        (0, "root"), (3, "fifth"), (4, "root"), (7, "fifth"),
        (8, "root"), (11, "fifth"), (12, "root"), (15, "fifth"),
    ],
    "octave_pulse": [(0, "root"), (2, "root"), (8, "root"), (10, "root")],
    "staccato": [(2, "root"), (6, "fifth"), (10, "root"), (14, "fifth")],
    "sub_drop": [(0, "root"), (8, "fifth"), (12, "root")],
}


def _build_bass_catalog() -> tuple[dict[str, list[BassStep]], list[str], dict[str, str]]:
    patterns: dict[str, list[BassStep]] = {}
    pool: list[str] = []
    aliases: dict[str, str] = {}
    for family, steps_a in _BASS_BASE.items():
        cid_a = f"{family}_a"
        patterns[cid_a] = steps_a
        pool.append(cid_a)
        aliases[family] = cid_a
        cid_b = f"{family}_b"
        patterns[cid_b] = _BASS_VARIANT_B.get(family, steps_a)
        pool.append(cid_b)
    return patterns, pool, aliases


BASS_VARIANT_PATTERNS, BASS_VARIANT_POOL, BASS_PATTERN_ALIASES = _build_bass_catalog()
