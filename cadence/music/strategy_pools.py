"""Pools de estrategias compositivas — selección determinista por generation_seed."""

from cadence.schemas.song_state import GenerationStrategies
from cadence.music.arp_patterns import ARP_PATTERNS

# ── Patrones de batería (16 steps, 4/4) ───────────────────────

DRUM_PATTERNS: dict[str, dict[str, list[int]]] = {
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
    "default": {
        "kick":  [1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "hihat": [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    },
}

DRUM_POOL = ["techno", "dubstep", "house", "breakbeat", "default"]

# ── Patrones de bajo (step, root|fifth) ───────────────────────

BassStep = tuple[int, str]

BASS_PATTERNS: dict[str, list[BassStep]] = {
    "root_fifth": [(0, "root"), (4, "root"), (8, "fifth"), (12, "root")],
    "driving": [(0, "root"), (3, "root"), (8, "fifth"), (11, "fifth")],
    "syncopated": [(2, "root"), (6, "fifth"), (10, "root"), (14, "fifth")],
    "pulse": [(0, "root"), (8, "root")],
}

BASS_POOL = list(BASS_PATTERNS.keys())

# ── Pools de progresiones armónicas ───────────────────────────

PROGRESSIONS_CLASSIC_MINOR = {
    "default": [(0, "minor"), (5, "major"), (2, "major"), (6, "major")],
    "tension": [(0, "minor"), (3, "minor"), (5, "major"), (4, "dominant")],
    "climax": [(0, "minor"), (0, "minor"), (6, "major"), (5, "major")],
    "sparse": [(0, "minor")],
    "release": [(0, "minor"), (5, "major"), (3, "minor"), (0, "minor")],
}

PROGRESSIONS_MODAL_MINOR = {
    "default": [(0, "minor"), (3, "minor"), (5, "major"), (0, "minor")],
    "tension": [(0, "minor"), (5, "major"), (6, "major"), (4, "dominant")],
    "climax": [(0, "minor"), (6, "major"), (5, "major"), (0, "minor")],
    "sparse": [(0, "minor"), (5, "major")],
    "release": [(0, "minor"), (5, "major"), (0, "minor")],
}

PROGRESSIONS_GAME_MINOR = {
    "default": [(0, "minor"), (6, "major"), (3, "minor"), (5, "major")],
    "tension": [(0, "minor"), (4, "dominant"), (5, "major"), (6, "major")],
    "climax": [(0, "minor"), (5, "major"), (4, "dominant"), (0, "minor")],
    "sparse": [(0, "minor")],
    "release": [(0, "minor"), (3, "minor"), (5, "major"), (0, "minor")],
}

PROGRESSIONS_CLASSIC_MAJOR = {
    "default": [(0, "major"), (4, "major"), (5, "minor"), (3, "major")],
    "tension": [(0, "major"), (5, "minor"), (3, "minor"), (4, "major")],
    "climax": [(0, "major"), (0, "major"), (5, "major"), (4, "major")],
    "sparse": [(0, "major")],
    "release": [(0, "major"), (4, "major"), (5, "minor"), (0, "major")],
}

PROGRESSIONS_MODAL_MAJOR = {
    "default": [(0, "major"), (5, "minor"), (3, "minor"), (4, "major")],
    "tension": [(0, "major"), (2, "minor"), (5, "minor"), (4, "major")],
    "climax": [(0, "major"), (5, "major"), (4, "major"), (0, "major")],
    "sparse": [(0, "major")],
    "release": [(0, "major"), (3, "major"), (0, "major")],
}

PROGRESSIONS_GAME_MAJOR = {
    "default": [(0, "major"), (5, "major"), (3, "minor"), (4, "major")],
    "tension": [(0, "major"), (6, "minor"), (4, "major"), (5, "major")],
    "climax": [(0, "major"), (4, "major"), (5, "major"), (0, "major")],
    "sparse": [(0, "major")],
    "release": [(0, "major"), (5, "minor"), (0, "major")],
}

HARMONY_POOLS_MINOR: dict[str, dict] = {
    "classic": PROGRESSIONS_CLASSIC_MINOR,
    "modal": PROGRESSIONS_MODAL_MINOR,
    "game": PROGRESSIONS_GAME_MINOR,
}

HARMONY_POOLS_MAJOR: dict[str, dict] = {
    "classic": PROGRESSIONS_CLASSIC_MAJOR,
    "modal": PROGRESSIONS_MODAL_MAJOR,
    "game": PROGRESSIONS_GAME_MAJOR,
}

HARMONY_POOL = ["classic", "modal", "game"]


def compute_generation_seed(raw_prompt: str, total_bars: int) -> int:
    return abs(hash(f"{raw_prompt}:{total_bars}")) % 100_000


def _genre_drum_bias(genre_tags: list[str]) -> list[str]:
    """Ordena candidatos de batería priorizando tags del prompt."""
    tags_lower = [t.lower() for t in genre_tags]
    preferred: list[str] = []
    for pool_id in DRUM_POOL:
        if pool_id in tags_lower:
            preferred.append(pool_id)
    for pool_id in DRUM_POOL:
        if pool_id not in preferred:
            preferred.append(pool_id)
    return preferred


def select_strategies(
    generation_seed: int,
    genre_tags: list[str],
    mode: str = "minor",
) -> GenerationStrategies:
    """Elige una estrategia de cada pool usando generation_seed."""
    drum_candidates = _genre_drum_bias(genre_tags)
    drum_pattern = drum_candidates[generation_seed % len(drum_candidates)]

    bass_pattern = BASS_POOL[(generation_seed // 7) % len(BASS_POOL)]
    harmony_pool = HARMONY_POOL[(generation_seed // 13) % len(HARMONY_POOL)]
    arp_pattern = ARP_PATTERNS[(generation_seed // 17) % len(ARP_PATTERNS)]

    return GenerationStrategies(
        generation_seed=generation_seed,
        drum_pattern=drum_pattern,
        bass_pattern=bass_pattern,
        harmony_pool=harmony_pool,
        arp_pattern=arp_pattern,
    )


def get_drum_pattern(pattern_id: str) -> dict[str, list[int]]:
    return DRUM_PATTERNS.get(pattern_id, DRUM_PATTERNS["default"])


def get_bass_pattern(pattern_id: str) -> list[BassStep]:
    return BASS_PATTERNS.get(pattern_id, BASS_PATTERNS["root_fifth"])


def get_harmony_templates(mode: str, pool_id: str) -> dict:
    pools = HARMONY_POOLS_MINOR if mode == "minor" else HARMONY_POOLS_MAJOR
    return pools.get(pool_id, pools["classic"])
