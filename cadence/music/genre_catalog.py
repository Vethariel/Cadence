"""Catálogo amplio de géneros musicales para perfiles de estilo y composición."""

from __future__ import annotations

# Categoría → géneros canónicos (minúsculas, sin espacios extra)
GENRE_CATALOG: dict[str, list[str]] = {
    "electronic_dance": [
        "techno", "house", "deep house", "progressive house", "electro house",
        "trance", "progressive trance", "psytrance", "hard trance",
        "eurodance", "eurobeat", "italo disco", "disco house",
        "hardstyle", "hardcore", "gabber", "happy hardcore",
        "drum and bass", "jungle", "liquid dnb", "neurofunk",
        "breakbeat", "big beat", "breakcore", "footwork",
        "garage", "uk garage", "2-step", "speed garage",
        "acid", "acid techno", "acid house", "minimal techno",
        "tech house", "melodic techno", "industrial techno",
    ],
    "bass_and_beats": [
        "dubstep", "brostep", "riddim", "melodic dubstep", "future bass",
        "trap", "hybrid trap", "bass music", "wonky",
        "moombahton", "reggaeton", "dancehall", "dembow",
        "phonk", "drill", "grime", "uk drill",
    ],
    "synth_retro_game": [
        "chiptune", "8-bit", "bitpop", "demoscene", "vgm", "video game music",
        "snes", "nintendo", "sega", "arcade", "retro gaming",
        "synthwave", "retrowave", "outrun", "darksynth", "cyberpunk",
        "electro", "electroclash", "new wave", "synthpop",
    ],
    "ambient_downtempo": [
        "ambient", "dark ambient", "drone", "space ambient",
        "chillout", "downtempo", "trip hop", "illbient",
        "idm", "glitch", "glitch hop", "microhouse",
        "lo-fi", "lo-fi hip-hop", "vaporwave", "mallsoft",
        "new age", "meditation", "soundscape",
    ],
    "industrial_dark": [
        "industrial", "ebm", "aggrotech", "darkwave", "coldwave",
        "dark techno", "dark electro", "power noise",
        "gothic", "gothic rock", "post-punk", "shoegaze",
        "noise", "harsh noise", "witch house",
    ],
    "rock": [
        "rock", "classic rock", "hard rock", "arena rock",
        "punk", "pop punk", "post-punk", "garage rock",
        "indie rock", "alternative rock", "grunge", "shoegaze rock",
        "progressive rock", "art rock", "math rock", "post-rock",
        "surf rock", "rockabilly", "psych rock",
    ],
    "metal": [
        "metal", "heavy metal", "thrash metal", "speed metal",
        "death metal", "black metal", "doom metal", "sludge",
        "metalcore", "deathcore", "djent", "progressive metal",
        "power metal", "symphonic metal", "folk metal", "nu metal",
        "industrial metal", "groove metal",
    ],
    "orchestral_cinematic": [
        "orchestral", "symphonic", "chamber", "baroque", "classical",
        "romantic", "neoclassical", "contemporary classical",
        "cinematic", "epic", "soundtrack", "film score",
        "trailer music", "hybrid orchestral", "neo-orchestral",
        "fantasy orchestral", "medieval", "renaissance",
    ],
    "jazz_blues_funk": [
        "jazz", "swing", "big band", "bebop", "cool jazz",
        "fusion", "smooth jazz", "acid jazz", "nu jazz",
        "blues", "delta blues", "chicago blues", "blues rock",
        "funk", "p-funk", "disco funk", "go-go",
        "soul", "neo soul", "motown", "r&b", "contemporary r&b",
    ],
    "hip_hop": [
        "hip-hop", "boom bap", "east coast hip-hop", "west coast hip-hop",
        "trap rap", "cloud rap", "conscious hip-hop",
        "instrumental hip-hop", "beat tape",
    ],
    "pop_world_folk": [
        "pop", "synthpop", "electropop", "indie pop", "dream pop",
        "k-pop", "j-pop", "city pop",
        "folk", "indie folk", "celtic", "nordic folk", "bluegrass",
        "country", "americana", "world", "ethnic", "tribal",
        "latin", "salsa", "bossa nova", "samba", "tango", "flamenco",
        "reggae", "dub", "ska", "afrobeat", "middle eastern",
        "bollywood", "carnatic", "gamelan",
    ],
    "game_context": [
        "boss fight", "battle", "combat", "action", "adventure",
        "exploration", "overworld", "dungeon", "stealth", "horror game",
        "puzzle", "platformer", "racing", "sports", "fighting game",
        "rpg", "jrpg", "visual novel", "menu theme", "shop",
        "victory", "game over", "level complete", "cutscene",
        "party game", "co-op", "mmo", "survival", "sandbox",
    ],
    "mood_energy": [
        "aggressive", "dark", "energetic", "epic mood", "heroic",
        "melancholic", "sad", "tense", "suspense", "mysterious",
        "ethereal", "dreamy", "whimsical", "playful", "uplifting",
        "triumphant", "ominous", "creepy", "horror mood", "romantic",
        "nostalgic", "hopeful", "calm", "relaxing", "intense",
    ],
}

# Alias → género canónico del catálogo
GENRE_ALIASES: dict[str, str] = {
    "8bit": "8-bit",
    "bit": "chiptune",
    "chip": "chiptune",
    "chip tune": "chiptune",
    "video games": "video game music",
    "game music": "video game music",
    "sound track": "soundtrack",
    "film music": "film score",
    "movie score": "film score",
    "dnb": "drum and bass",
    "drum n bass": "drum and bass",
    "drum & bass": "drum and bass",
    "edm": "house",
    "bro step": "brostep",
    "future bass music": "future bass",
    "hip hop": "hip-hop",
    "hiphop": "hip-hop",
    "rnb": "r&b",
    "r and b": "r&b",
    "d&b": "drum and bass",
    "psy trance": "psytrance",
    "hard core": "hardcore",
    "synth wave": "synthwave",
    "retro wave": "retrowave",
    "dark synth": "darksynth",
    "lo fi": "lo-fi",
    "lofi": "lo-fi",
    "boss": "boss fight",
    "boss battle": "boss fight",
    "final boss": "boss fight",
    "fight": "battle",
    "orchestra": "orchestral",
    "symphony": "symphonic",
    "cinematic orchestral": "hybrid orchestral",
    "epic orchestral": "epic",
    "industrial rock": "industrial",
    "techno industrial": "industrial techno",
    "super nintendo": "snes",
    "n64": "video game music",
    "arcade game": "arcade",
    "party": "party game",
    "super bomberman": "party game",
}

_ALL_GENRES: list[str] | None = None
_GENRE_INDEX: dict[str, str] | None = None


def _build_index() -> tuple[list[str], dict[str, str]]:
    genres: list[str] = []
    index: dict[str, str] = {}
    for items in GENRE_CATALOG.values():
        for g in items:
            if g not in genres:
                genres.append(g)
            index[g.lower()] = g
    for alias, canonical in GENRE_ALIASES.items():
        index[alias.lower()] = canonical
    return genres, index


def all_genres() -> list[str]:
    """Lista plana de todos los géneros canónicos, en orden estable."""
    global _ALL_GENRES, _GENRE_INDEX
    if _ALL_GENRES is None:
        _ALL_GENRES, _GENRE_INDEX = _build_index()
    return list(_ALL_GENRES)


def _genre_index() -> dict[str, str]:
    global _ALL_GENRES, _GENRE_INDEX
    if _GENRE_INDEX is None:
        _ALL_GENRES, _GENRE_INDEX = _build_index()
    return _GENRE_INDEX


def normalize_genre(tag: str) -> str:
    """
    Mapea una etiqueta libre al género canónico del catálogo.
    Si no hay match, devuelve el tag limpio (permite extensiones raras).
    """
    raw = tag.strip()
    if not raw:
        return raw
    key = raw.lower()
    index = _genre_index()
    if key in index:
        return index[key]
    for canonical in all_genres():
        cl = canonical.lower()
        if key == cl or key in cl or cl in key:
            return canonical
    return raw


def normalize_genres(tags: list[str], *, max_count: int = 8) -> list[str]:
    """Normaliza y deduplica géneros; limita a max_count."""
    seen: set[str] = set()
    out: list[str] = []
    for tag in tags:
        norm = normalize_genre(tag)
        key = norm.lower()
        if key and key not in seen:
            seen.add(key)
            out.append(norm)
        if len(out) >= max_count:
            break
    return out


def format_genre_catalog_for_llm(*, compact: bool = True) -> str:
    """
    Formato para prompts LLM.
    compact=True: una línea por categoría (menos tokens).
    """
    lines = ["=== CATÁLOGO DE GÉNEROS (elige 3–8 ids canónicos) ==="]
    for category, genres in GENRE_CATALOG.items():
        label = category.replace("_", " ").title()
        if compact:
            lines.append(f"{label}: {', '.join(genres)}")
        else:
            lines.append(f"\n{label}:")
            for g in genres:
                lines.append(f"  • {g}")
    lines.append(
        "\nUsa EXACTAMENTE estos ids en `genres`. "
        "Referencias concretas (juegos, artistas) van en `references`, no en genres."
    )
    return "\n".join(lines)


def genres_in_category(category: str) -> list[str]:
    return list(GENRE_CATALOG.get(category, []))


_GENRE_TO_CATEGORY: dict[str, str] | None = None


def _build_genre_to_category() -> dict[str, str]:
    index: dict[str, str] = {}
    for category, genres in GENRE_CATALOG.items():
        for g in genres:
            index[g.lower()] = category
            index[normalize_genre(g).lower()] = category
    for alias, canonical in GENRE_ALIASES.items():
        cat = index.get(canonical.lower())
        if cat:
            index[alias.lower()] = cat
    return index


def category_for_genre(genre: str) -> str | None:
    """Categoría del catálogo para un género canónico o alias."""
    global _GENRE_TO_CATEGORY
    if _GENRE_TO_CATEGORY is None:
        _GENRE_TO_CATEGORY = _build_genre_to_category()
    key = normalize_genre(genre).lower()
    return _GENRE_TO_CATEGORY.get(key)


def category_mix_from_genres(genres: list[str]) -> dict[str, float]:
    """Pesos por categoría a partir de etiquetas (sin normalizar a suma 1)."""
    weights: dict[str, float] = {}
    for tag in genres:
        norm = normalize_genre(tag)
        cat = category_for_genre(norm)
        if cat:
            weights[cat] = weights.get(cat, 0.0) + 1.0
    total = sum(weights.values())
    if total <= 0:
        return {}
    return {c: round(w / total, 4) for c, w in weights.items()}


def category_mix_from_genre_mix(genre_mix: dict[str, float]) -> dict[str, float]:
    """Agrega genre_mix canónico en pesos por categoría del catálogo."""
    weights: dict[str, float] = {}
    for genre, w in genre_mix.items():
        if w <= 0:
            continue
        cat = category_for_genre(genre)
        if cat:
            weights[cat] = weights.get(cat, 0.0) + w
    total = sum(weights.values())
    if total <= 0:
        return {}
    return {c: round(v / total, 4) for c, v in weights.items()}


def dominant_category(
    category_mix: dict[str, float],
    *,
    default: str | None = None,
) -> str | None:
    if not category_mix:
        return default
    return max(category_mix.items(), key=lambda x: x[1])[0]
